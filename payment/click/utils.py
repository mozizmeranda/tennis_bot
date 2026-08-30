"""
Вспомогательные утилиты Click.uz:
- тонкие обёртки над методами db для handlers.py
- формирование ссылки на оплату
"""

from urllib.parse import urlencode
from database.database import db
from config.config import (
    CLICK_MERCHANT_ID,
    CLICK_SERVICE_ID,
    CLICK_RETURN_URL,
)

# db = Database()


# ---------------------------------------------------------------------------
# Работа с базой данных — делегируем методам db
# ---------------------------------------------------------------------------

async def click_create_order(order_id: str, telegram_id: int, amount: float) -> int:
    return await db.create_order(order_id, telegram_id, amount)


async def get_order(order_id: int) -> dict | None:
    return await db.get_order(order_id)


async def set_click_trans_id(order_id: int, click_trans_id: int) -> None:
    await db.set_click_trans_id(order_id, click_trans_id)


async def mark_order_paid(order_id: int, payment_id: int) -> None:
    await db.mark_order_paid(order_id, payment_id)


async def mark_order_failed(order_id: int, error_code: int) -> None:
    await db.mark_order_failed(order_id, error_code)


async def mark_order_cancelled(order_id: int, error_code: int) -> None:
    await db.mark_order_cancelled(order_id, error_code)


# ---------------------------------------------------------------------------
# Формирование ссылки для оплаты
# ---------------------------------------------------------------------------

def build_payment_url(order_id: int, amount: float) -> str:
    """
    Возвращает ссылку для редиректа пользователя на страницу Click.

    Пример использования:
        url = build_payment_url(order_id=789, amount=5000.0)
        # Telegram Mini App:  window.Telegram.WebApp.openLink(url)
        # Обычный бот:        InlineKeyboardButton("Оплатить", url=url)
    """
    params = urlencode({
        "service_id":        CLICK_SERVICE_ID,
        "merchant_id":       CLICK_MERCHANT_ID,
        "amount":            f"{amount:.2f}",
        "transaction_param": str(order_id),
        "return_url":        CLICK_RETURN_URL,
    })
    return f"https://my.click.uz/services/pay?{params}"
