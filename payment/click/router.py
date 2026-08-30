"""
FastAPI-роутер для Click.uz.

Подключение в main.py:
    from click.router import router as click_router
    app.include_router(click_router)

Эндпоинты:
    POST /click/prepare   — вызывается Click до списания денег
    POST /click/complete  — вызывается Click после попытки списания
    POST /orders          — создание заказа до редиректа на Click
    GET  /orders/{id}/status — проверка статуса заказа (для Mini App)
"""

import logging
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from .handlers import handle_prepare, handle_complete
from .utils import click_create_order, get_order, build_payment_url
from config.models import CreateInvoiceRequest

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Click"])
orders_router = APIRouter(prefix="/orders", tags=["Orders"])


# ---------------------------------------------------------------------------
# Click webhooks
# ---------------------------------------------------------------------------


@router.get("/get_invoice_link/{order_id}")
async def click_get_invoice_link(order_id: str):
    pass


@router.post("/create_invoice")
async def click_create_invoice(body: CreateInvoiceRequest):
    """
    Создаёт заказ в БД и возвращает ссылку для оплаты через Click.

    Пример запроса:
        POST /orders?user_id=123456789&amount=5000&description=Подписка
    """
    amount_tiyins = body.price * 100
    order_id = await click_create_order(order_id=body.temporary_booking_id, telegram_id=body.telegram_id, amount=amount_tiyins)
    payment_url = build_payment_url(order_id=order_id, amount=body.price)

    return {
        "order_id": order_id,
        "amount": body.price,
        "payment_url": payment_url,
    }


@router.post("/prepare")
async def click_prepare(request: Request):
    """
    Вызывается Click до списания денег.
    Проверяем заказ и подпись, возвращаем подтверждение.
    """
    data = await request.form()
    data = dict(data)
    logger.info("[Click][Prepare] Incoming: %s", data)

    result = await handle_prepare(data)
    return JSONResponse(content=result)


@router.post("/complete")
async def click_complete(request: Request):
    """
    Вызывается Click после попытки списания (успешной или нет).
    Обновляем статус заказа.
    """
    data = await request.form()
    data = dict(data)
    logger.info("[Click][Complete] Incoming: %s", data)

    result = await handle_complete(data)
    return JSONResponse(content=result)


# ---------------------------------------------------------------------------
# Заказы
# ---------------------------------------------------------------------------

@orders_router.post("")
async def create_new_order(user_id: int, amount: float, description: str = ""):
    """
    Создаёт заказ в БД и возвращает ссылку для оплаты через Click.

    Пример запроса:
        POST /orders?user_id=123456789&amount=5000&description=Подписка
    """
    order_id = await create_order(user_id=user_id, amount=amount, description=description)
    payment_url = build_payment_url(order_id=order_id, amount=amount)

    return {
        "order_id":    order_id,
        "amount":      amount,
        "payment_url": payment_url,
    }


@orders_router.get("/{order_id}/status")
async def get_order_status(order_id: int):
    """
    Возвращает текущий статус заказа.
    Используется Mini App после возврата из Click (return_url),
    чтобы убедиться что Complete уже пришёл.

    Статусы: pending | paid | failed | cancelled
    """
    order = await get_order(order_id)
    if not order:
        return JSONResponse(status_code=404, content={"error": "Order not found"})

    return {
        "order_id": order_id,
        "status":   order["status"],
        "amount":   order["amount"],
    }