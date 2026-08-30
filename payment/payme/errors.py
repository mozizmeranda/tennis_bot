"""
errors.py — Коды ошибок Payme и хелперы для формирования ответов.
"""


# ──────────────────────────────────────────
#  Коды ошибок (возвращаем МЫ → Payme)
# ──────────────────────────────────────────

INVALID_AMOUNT        = -31001  # сумма не совпадает с ценой заказа
TRANSACTION_NOT_FOUND = -31003  # транзакция не найдена в нашей БД
CANT_PERFORM_CANCEL   = -31007  # нельзя отменить — услуга уже оказана
UNABLE_TO_PERFORM     = -31008  # невозможно выполнить (напр. создать отменённую транзакцию)
ORDER_NOT_FOUND       = -31050  # заказ не найден (account.order_id неверный)
SERVER_ERROR          = -32400  # системная ошибка на нашей стороне
AUTHORIZATION_FAILED  = -32504  # неверный ключ авторизации
ORDER_IN_PROGRESS     = -31051  # Заказ уже находится в процессе оплаты
ORDER_ALREADY_PAID    = -31052  # Заказ уже оплачен
ORDER_IS_WAITING_FOR_PAYMENT = -31053
ORDER_ALREADY_CANCELLED = -31054  # Заказ уже отменен
ORDER_CANCELLED_OR_BLOCKED = -31055  # Заказ был отменен


# ──────────────────────────────────────────
#  Хелперы для формирования ответов
# ──────────────────────────────────────────

def ok(result: dict, request_id) -> dict:
    """Успешный ответ."""
    return {"result": result, "id": request_id}


def error(code: int, message, request_id, data: str | None = None) -> dict:
    """
    Ответ с ошибкой.

    message — строка ИЛИ dict {"ru": ..., "uz": ..., "en": ...}
    data    — название субполя account, которое не прошло проверку (необязательно)
    """
    err: dict = {"code": code, "message": message}
    if data is not None:
        err["data"] = data
    return {"error": err, "id": request_id}


def err(code: int, message, request_id, data: str | None = None) -> dict:
    """
    Ответ с ошибкой.

    message — строка ИЛИ dict {"ru": ..., "uz": ..., "en": ...}
    data    — название субполя account, которое не прошло проверку (необязательно)
    """
    err: dict = {"code": code, "message": message}
    if data is not None:
        err["data"] = data
    return {"error": err, "id": request_id}


# ──────────────────────────────────────────
#  Готовые сообщения об ошибках (многоязычные)
# ──────────────────────────────────────────

MSG_ORDER_NOT_FOUND = {
    "ru": "Заказ не найден",
    "uz": "Buyurtma topilmadi",
    "en": "Order not found",
}

MSG_INVALID_AMOUNT = {
    "ru": "Неверная сумма",
    "uz": "Noto'g'ri summa",
    "en": "Invalid amount",
}

MSG_TRANSACTION_NOT_FOUND = {
    "ru": "Транзакция не найдена",
    "uz": "Tranzaksiya topilmadi",
    "en": "Transaction not found",
}

MSG_CANT_CANCEL = {
    "ru": "Невозможно отменить — услуга уже оказана",
    "uz": "Bekor qilib bo'lmaydi — xizmat allaqachon ko'rsatilgan",
    "en": "Cannot cancel — service already provided",
}

MSG_UNABLE_TO_PERFORM = {
    "ru": "Невозможно выполнить операцию",
    "uz": "Amalni bajarib bo'lmaydi",
    "en": "Unable to perform operation",
}

MSG_ORDER_IN_PROGRESS = {
    "ru": "Заказ уже находится в процессе оплаты другой транзакцией",
    "uz": "Buyurtma allaqachon boshqa tranzaksiya orqali to'lov jarayonida",
    "en": "The order is already in the payment process by another transaction",
}


MSG_ORDER_ALREADY_PAID = {
    "ru": "Этот заказ уже был успешно оплачен",
    "uz": "Ushbu buyurtma uchun to'lov allaqachon muvaffaqiyatli amalga oshirilgan",
    "en": "This order has already been successfully paid",
}


MSG_ORDER_IS_WAITING_FOR_PAYMENT = {
    "ru": "Этот заказ уже обрабатывается другим",
    "uz": "Ushbu buyurtma obrabotkada",
    "en": "This order is waiting for the payment",
}

MSG_ORDER_ALREADY_CANCELLED = {
    "ru": "Этот заказ был отменен",
    "uz": "Ushbu buyurtma bekor qilingan",
    "en": "This order has been cancelled",
}


STATUS_ERROR_MAP = {
    "paid": (ORDER_ALREADY_PAID, MSG_ORDER_ALREADY_PAID),
    "waiting_for_payment": (ORDER_IN_PROGRESS, MSG_ORDER_IN_PROGRESS),
    "cancelled": (ORDER_ALREADY_CANCELLED, MSG_ORDER_ALREADY_CANCELLED),
}

MSG_ORDER_CANCELLED = {
    "ru": "Заказ был отменен",
    "uz": "Buyurtma bekor qilingan",
    "en": "Order has been cancelled",
}

# Для state = -2
MSG_ORDER_BLOCKED = {
    "ru": "Заказ заблокирован или аннулирован",
    "uz": "Buyurtma bloklangan yoki bekor qilingan",
    "en": "Order is blocked or invalidated",
}

