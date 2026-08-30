"""
handlers.py — Логика обработки каждого из 6 методов Payme.

Каждая функция принимает:
  - params: dict  — поле "params" из запроса Payme
  - req_id        — поле "id" из запроса (для ответа)
  - db: Database  — экземпляр твоего класса Database

Возвращает готовый dict для отправки обратно Payme.
"""
import logging
import time
from config.config import TIMEOUT_MS, PAYMENT_CACHE, TELEGRAM_TOKEN, CALENDAR_ID, locs
from database.database import Database, db
from network.client import get_http_client
from .errors import *
from .utils import t, texts

logger = logging.getLogger(__name__)


def _now_ms() -> int:
    return int(time.time() * 1000)


async def send_after_perform(chat_id, order_id, location, booking_date, time_slots, lang):
    client = get_http_client()

    # Исправлены кавычки внутри f-строки: t('location', lang) вместо t("location", lang)
    text = (f"Order_id: {order_id} \n{t('location', lang)}: {locs[location]} \n"
            f"{t('booking_date', lang)}: {booking_date} \n{t('time_slots', lang)}: {time_slots}\n\n")

    payload = {
        "chat_id": chat_id,
        "text": f"🎉{t('payment_confirmed', lang)}\n{text}\n\n{t('wait_us', lang)}\n"
    }

    # Делаем запрос напрямую через httpx client
    response = await client.post(
        f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
        json=payload
    )

    # Проверяем успешность (бросит исключение, если Telegram вернул ошибку)
    response.raise_for_status()


async def send_after_cancel(chat_id, order_id, location, booking_date, time_slots, lang):
    client = get_http_client()

    text = (f"Order_id: {order_id} \n{t('location', lang)}: {locs[location]} \n"
            f"{t('booking_date', lang)}: {booking_date} \n{t('time_slots', lang)}: {time_slots}\n\n")

    payload = {
        "chat_id": chat_id,
        "text": f"❌ {t('rejected', lang)} \n\n{text}\n\n{t('payment_rejected', lang)}\n{t('contact_admin', lang)}"
    }

    # Делаем запрос напрямую через httpx client
    response = await client.post(
        f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
        json=payload
    )

    # Проверяем успешность
    response.raise_for_status()


# ──────────────────────────────────────────
#  1. CheckPerformTransaction
#  Payme спрашивает: "Можно ли начать оплату?"
#  Деньги ещё НЕ списаны.
# ──────────────────────────────────────────
async def check_perform_transaction(params: dict, req_id) -> dict:
    order_id = params.get("account", {}).get("order_id")
    amount = params.get("amount")

    order = await db.get_order_by_id(order_id)
    if not order:
        logger.exception("Order is not found: order_id: %s", order_id)
        return error(ORDER_NOT_FOUND, MSG_ORDER_NOT_FOUND, req_id, data="order_id")

    # Сумма совпадает?
    if int(order["amount"]) != int(amount):
        return error(INVALID_AMOUNT, MSG_INVALID_AMOUNT, req_id, data="amount")

    current_status = order["status"]
    PAYMENT_CACHE[order_id] = current_status
    match current_status:
        case "paid":
            return error(ORDER_ALREADY_PAID, MSG_ORDER_ALREADY_PAID, req_id)
        case "waiting_payment":
            return error(ORDER_IN_PROGRESS, MSG_ORDER_IN_PROGRESS, req_id)
        case "cancelled":
            return error(ORDER_ALREADY_CANCELLED, MSG_ORDER_ALREADY_CANCELLED, req_id)
        # case "pending":
        #     return error(ORDER_IS_WAITING_FOR_PAYMENT, MSG_ORDER_IS_WAITING_FOR_PAYMENT, req_id)

    # Заказ ещё не оплачен и не в процессе?
    if current_status not in ("pending",):
        return error(UNABLE_TO_PERFORM, MSG_UNABLE_TO_PERFORM, req_id)

    return ok({"allow": True}, req_id)


# ──────────────────────────────────────────
#  2. CreateTransaction
#  Payme говорит: "Начинаю процесс, зафиксируй у себя."
#  Деньги ещё НЕ списаны.
# ──────────────────────────────────────────

async def create_transaction(params: dict, req_id) -> dict:
    payme_id = params.get("id")
    amount = params.get("amount")
    order_id = params.get("account", {}).get("order_id")
    create_time = params.get("time")

    logger.info("PAYME CREATE TRANSACTION: payme_id: %s, order_id: %s", payme_id, order_id)

    order = await db.get_payme_transaction_by_order_id(order_id)
    if not order:
        return error(ORDER_NOT_FOUND, MSG_ORDER_NOT_FOUND, req_id, data="order_id")

    if int(order["state"]) < 0:
        return error(ORDER_CANCELLED_OR_BLOCKED, MSG_ORDER_CANCELLED, req_id)

    existing = await db.get_payme_transaction(payme_id)
    now = time.time()
    if existing:
        # Если транзакция уже отменена — нельзя переоткрыть
        if existing["state"] != 1:
            return error(UNABLE_TO_PERFORM, MSG_UNABLE_TO_PERFORM, req_id)

        if (now - existing["create_time"]) > TIMEOUT_MS:
            await db.cancel_payme_transaction(order_id, payme_id, -1, 4, now)
            return error(UNABLE_TO_PERFORM, MSG_UNABLE_TO_PERFORM, req_id)

        # Иначе возвращаем то что уже есть
        return ok({
            "transaction": str(existing["id"]),
            "create_time": existing["create_time"],
            "state":       existing["state"],
        }, req_id)

    # Проверяем заказ (те же проверки что в Check)
    order = await db.get_order_by_id(order_id)
    if not order:
        return error(ORDER_NOT_FOUND, MSG_ORDER_NOT_FOUND, req_id, data="order_id")

    current_status = order["status"]
    PAYMENT_CACHE[order_id] = current_status

    if current_status == "paid":
        return error(ORDER_ALREADY_PAID, MSG_ORDER_ALREADY_PAID, req_id)

    if current_status == "waiting_payment":
        return error(ORDER_IN_PROGRESS, MSG_ORDER_IN_PROGRESS, req_id)

    if order["amount"] != amount:
        return error(INVALID_AMOUNT, MSG_INVALID_AMOUNT, req_id, data="amount")

    if current_status not in ("pending",):
        return error(UNABLE_TO_PERFORM, MSG_UNABLE_TO_PERFORM, req_id)

    # Создаём транзакцию и блокируем заказ
    PAYMENT_CACHE[order_id] = "waiting_payment"
    txn = await db.create_payme_transaction(payme_id, order_id, amount, create_time)
    # await db.set_order_status(order_id, "waiting_payment")
    logger.info("Successfully created txn: txn: %s", txn)

    return ok({
        "transaction": str(txn["id"]),
        "create_time": txn["create_time"],
        "state":       txn["state"],
    }, req_id)


# ──────────────────────────────────────────
#  3. PerformTransaction
#  Payme говорит: "Деньги списаны — подтверди."
#  Это момент когда заказ считается ОПЛАЧЕННЫМ.
# ──────────────────────────────────────────

async def perform_transaction(params: dict, req_id) -> dict:

    logger.info("Payme Perform transaction: params: %s, req_id: %s", params, req_id)

    payme_id = params.get("id")

    txn = await db.get_payme_transaction(payme_id)
    if not txn:
        return error(TRANSACTION_NOT_FOUND, MSG_TRANSACTION_NOT_FOUND, req_id)

    # Уже выполнена? Возвращаем без изменений (идемпотентность)
    if txn["state"] == 2:
        return ok({
            "transaction":   str(txn["id"]),
            "perform_time":  txn["perform_time"],
            "state":         2,
        }, req_id)

    # Можно выполнить только из state=1
    if txn["state"] != 1:
        return error(UNABLE_TO_PERFORM, MSG_UNABLE_TO_PERFORM, req_id)

    perform_time = _now_ms()

    if (perform_time - txn["create_time"]) > TIMEOUT_MS:
        PAYMENT_CACHE[txn["order_id"]] = "cancelled"
        await db.cancel_payme_transaction(txn["order_id"], payme_id, -1, 4, perform_time)
        return error(UNABLE_TO_PERFORM, MSG_UNABLE_TO_PERFORM, req_id)

    PAYMENT_CACHE[txn["order_id"]] = "paid"
    await db.perform_payme_transaction(txn["order_id"], payme_id, perform_time)

    data = await db.data_after_perform(txn["order_id"])
    if data:
        try:
            await send_after_perform(chat_id=data["chat_id"], order_id=txn["order_id"], location=data["location"],
                                     booking_date=data["booking_date"], time_slots=data["time_slots"], lang=data["lang"])
        except Exception:
            pass

    # await db.set_order_status(txn["order_id"], "paid")
    logger.info("Paid order: payme_id: %s, order_id: %s", payme_id)
    return ok({
        "transaction":  str(txn["id"]),
        "perform_time": perform_time,
        "state":        2,
    }, req_id)


# ──────────────────────────────────────────
#  4. CancelTransaction
#  Payme говорит: "Отменяю — верни заказ в исходный статус."
#  reason: 1=клиент отменил, 2=ошибка, 3=таймаут, 4=не подтверждено, 5=возврат
# ──────────────────────────────────────────

async def cancel_transaction(params: dict, req_id) -> dict:

    logger.info("Payme cancel transaction: params: %s, req_id: %s", params, req_id)

    payme_id = params.get("id")
    reason = params.get("reason")

    txn = await db.get_payme_transaction(payme_id)
    if not txn:
        return error(TRANSACTION_NOT_FOUND, MSG_TRANSACTION_NOT_FOUND, req_id)

    # Уже отменена? Возвращаем без изменений
    if txn["state"] in (-1, -2):
        return ok({
            "transaction": str(txn["id"]),
            "cancel_time": txn["cancel_time"],
            "state":       txn["state"],
        }, req_id)

    cancel_time = _now_ms()

    if txn["state"] == 1:
        # Ещё не оплачена — просто отменяем
        new_state = -1
        # await db.set_order_status(txn["order_id"], "cancelled")

    elif txn["state"] == 2:
        # Уже оплачена — это возврат.
        # Если услуга уже оказана — запрещаем отмену:
        return error(CANT_PERFORM_CANCEL, MSG_CANT_CANCEL, req_id)

    else:
        return error(UNABLE_TO_PERFORM, MSG_UNABLE_TO_PERFORM, req_id)

    PAYMENT_CACHE[txn["order_id"]] = "cancelled"
    resp = await db.cancel_payme_transaction(txn["order_id"], payme_id, new_state, reason, cancel_time)

    if resp == -1:
        return error(UNABLE_TO_PERFORM, MSG_UNABLE_TO_PERFORM, req_id)

    data = await db.data_after_perform(txn["order_id"])
    if data:
        try:
            await send_after_cancel(chat_id=data["chat_id"], order_id=txn["order_id"], location=data["location"],
                                    booking_date=data["booking_date"], time_slots=data["time_slots"], lang=data["lang"])
        except Exception:
            pass

    return ok({
        "transaction": str(txn["id"]),
        "cancel_time": cancel_time,
        "state":       new_state,
    }, req_id)


# ──────────────────────────────────────────
#  5. CheckTransaction
#  Payme проверяет статус конкретной транзакции.
# ──────────────────────────────────────────

async def check_transaction(params: dict, req_id) -> dict:
    payme_id = params.get("id")

    txn = await db.get_payme_transaction(payme_id)
    if not txn:
        return error(TRANSACTION_NOT_FOUND, MSG_TRANSACTION_NOT_FOUND, req_id)

    return ok({
        "create_time": txn["create_time"] or 0,
        "perform_time": txn["perform_time"] or 0,
        "cancel_time": txn["cancel_time"] or 0,
        "transaction": str(txn["id"]),
        "state": txn["state"],
        "reason": txn["reason"],  # это поле как раз может быть null
    }, req_id)


# ──────────────────────────────────────────
#  6. GetStatement
#  Payme запрашивает список транзакций за период.
#  Используется для сверки.
# ──────────────────────────────────────────

async def get_statement(params: dict, req_id) -> dict:
    from_time = params.get("from")
    to_time   = params.get("to")

    transactions = await db.get_payme_transactions_by_range(from_time, to_time)

    return ok({
        "transactions": [
            {
                "id":           txn["payme_id"],
                "time":         txn["create_time"],
                "amount":       txn["amount"],
                "account":      {"order_id": txn["order_id"]},
                "create_time":  txn["create_time"],
                "perform_time": txn["perform_time"] or 0,
                "cancel_time":  txn["cancel_time"] or 0,
                "transaction":  str(txn["id"]),
                "state":        txn["state"],
                "reason":       txn["reason"],
            }
            for txn in transactions
        ]
    }, req_id)
