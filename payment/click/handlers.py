"""
Бизнес-логика обработчиков /click/prepare и /click/complete.
Вызывается из router.py.
"""

import logging
from .errors import (
    SUCCESS, INVALID_SIGN, INVALID_AMOUNT, ALREADY_PAID,
    ORDER_NOT_FOUND, SERVER_ERROR, CLICK_STATUS_MAP,
)
from .auth import verify_sign
from .utils import get_order, set_click_trans_id, mark_order_paid, mark_order_failed, mark_order_cancelled
import base64

logger = logging.getLogger(__name__)


async def handle_prepare(data: dict) -> dict:
    """
    Обработчик Prepare-запроса от Click.

    1. Проверяем MD5-подпись
    2. Находим заказ
    3. Проверяем статус и сумму
    4. Сохраняем click_trans_id
    5. Возвращаем ответ Click
    """
    click_trans_id = int(data.get("click_trans_id", 0))
    merchant_trans_id = str(data.get("merchant_trans_id", ""))

    logger.info("[Click][Prepare] click_trans_id=%s merchant_trans_id=%s",
                click_trans_id, merchant_trans_id)

    # 1. Проверка подписи
    if not verify_sign(data):
        logger.warning("[Click][Prepare] Invalid sign for merchant_trans_id=%s", merchant_trans_id)
        return INVALID_SIGN.as_dict(click_trans_id, merchant_trans_id)

    # 2. Находим заказ
    try:
        order_id = int(merchant_trans_id)
    except ValueError:
        return ORDER_NOT_FOUND.as_dict(click_trans_id, merchant_trans_id)

    order = await get_order(order_id)

    if not order:
        return ORDER_NOT_FOUND.as_dict(click_trans_id, merchant_trans_id)

    # 3. Проверяем статус
    if order["status"] != "pending":
        return ALREADY_PAID.as_dict(click_trans_id, merchant_trans_id)

    # 4. Проверяем сумму (с допуском 0.01 сума)
    incoming_amount = float(data.get("amount", 0))
    if abs(incoming_amount - order["amount"]) > 0.01:
        logger.warning(
            "[Click][Prepare] Amount mismatch: expected %.2f, got %.2f",
            order["amount"], incoming_amount,
        )
        return INVALID_AMOUNT.as_dict(click_trans_id, merchant_trans_id)

    # 5. Сохраняем click_trans_id
    await set_click_trans_id(order_id, click_trans_id)

    logger.info("[Click][Prepare] OK for order_id=%s", order_id)

    return {
        "click_trans_id":      click_trans_id,
        "merchant_trans_id":   merchant_trans_id,
        "merchant_prepare_id": order_id,
        "error":               SUCCESS.code,
        "error_note":          SUCCESS.note,
    }


async def handle_complete(data: dict) -> dict:
    """
    Обработчик Complete-запроса от Click.

    1. Проверяем подпись
    2. Находим заказ и проверяем merchant_prepare_id
    3. Обновляем статус заказа согласно data["error"]
    4. Всегда возвращаем error=0 (это ответ нашего сервера, не статус платежа)
    """
    click_trans_id    = int(data.get("click_trans_id", 0))
    merchant_trans_id = str(data.get("merchant_trans_id", ""))
    payment_id        = int(data.get("payment_id", 0))
    click_error       = int(data.get("error", -9))

    logger.info(
        "[Click][Complete] click_trans_id=%s merchant_trans_id=%s payment_id=%s click_error=%s",
        click_trans_id, merchant_trans_id, payment_id, click_error,
    )

    # 1. Проверка подписи
    if not verify_sign(data):
        logger.warning("[Click][Complete] Invalid sign for merchant_trans_id=%s", merchant_trans_id)
        return INVALID_SIGN.as_dict(click_trans_id, merchant_trans_id)

    # 2. Находим заказ
    try:
        order_id = int(merchant_trans_id)
    except ValueError:
        return ORDER_NOT_FOUND.as_dict(click_trans_id, merchant_trans_id)

    order = await get_order(order_id)

    if not order:
        return ORDER_NOT_FOUND.as_dict(click_trans_id, merchant_trans_id)

    # Идемпотентность: уже обработанный заказ не трогаем
    if order["status"] == "paid":
        logger.info("[Click][Complete] Order %s already paid, skipping", order_id)
        return {
            "click_trans_id":    click_trans_id,
            "merchant_trans_id": merchant_trans_id,
            "error":             SUCCESS.code,
            "error_note":        SUCCESS.note,
        }

    # 3. Обновляем статус
    new_status = CLICK_STATUS_MAP.get(click_error, "failed")

    if new_status == "paid":
        await mark_order_paid(order_id, payment_id)
        logger.info("[Click][Complete] Order %s marked as PAID, payment_id=%s", order_id, payment_id)

        # ✅ Здесь добавьте выдачу товара / активацию подписки / уведомление пользователя
        # await notify_user(order["user_id"], "Оплата прошла успешно!")

    elif new_status == "cancelled":
        await mark_order_cancelled(order_id, click_error)
        logger.info("[Click][Complete] Order %s CANCELLED by user", order_id)

    else:
        await mark_order_failed(order_id, click_error)
        logger.warning("[Click][Complete] Order %s FAILED with click_error=%s", order_id, click_error)

    # 4. Всегда отвечаем Click success (иначе он будет повторять запросы)
    return {
        "click_trans_id":    click_trans_id,
        "merchant_trans_id": merchant_trans_id,
        "error":             SUCCESS.code,
        "error_note":        SUCCESS.note,
    }

