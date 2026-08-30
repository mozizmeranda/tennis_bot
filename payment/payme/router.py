"""
router.py — Единственный endpoint для Payme.

Подключи в main.py:
    from payment.router import router
    app.include_router(router)
"""

from fastapi import APIRouter, Request, status
from fastapi.responses import JSONResponse

from config.models import CreateInvoiceRequest
from config.config import PAYMENT_CACHE
from database.database import db
from .auth import check_auth
from .handlers import (
    check_perform_transaction,
    create_transaction,
    perform_transaction,
    cancel_transaction,
    check_transaction,
    get_statement
)
from .utils import generate_payme_url
import logging

logger = logging.getLogger(__name__)

router = APIRouter()
# db = Database()

METHODS = {
    "CheckPerformTransaction": check_perform_transaction,
    "CreateTransaction":       create_transaction,
    "PerformTransaction":      perform_transaction,
    "CancelTransaction":       cancel_transaction,
    "CheckTransaction":        check_transaction,
    "GetStatement":            get_statement,
}


@router.post("")
async def payme_endpoint(request: Request):
    body = await request.json()

    req_id = body.get("id")
    method = body.get("method")
    params = body.get("params", {})

    logger.info("Payme Method Endpoint, body: %s", body)
    # Проверка авторизации
    auth_error = await check_auth(request, req_id)
    if auth_error:
        return JSONResponse(auth_error)

    # Роутинг по method
    handler = METHODS.get(method)
    if not handler:
        return JSONResponse({
            "error": {"code": -32601, "message": "Method not found"},
            "id": req_id,
        })

    result = await handler(params, req_id)
    return JSONResponse(result)


@router.post("/create_invoice")
async def create_invoice_func(body: CreateInvoiceRequest):

    logger.info("Payme Create Invoice: body: %s", body.model_dump())

    temporary_booking_id = body.temporary_booking_id
    telegram_id = body.telegram_id
    price = body.price
    location = body.location

    PAYMENT_CACHE[temporary_booking_id] = "pending"
    amount = price * 100  # в тийинах
    # description = f"Корт {location}: {', '.join(time_slots)}"

    order_id = await db.create_order(
        order_id=temporary_booking_id,
        user_id=telegram_id,
        amount=amount,
    )

    if order_id == 0:
        payment_url = await generate_payme_url(order_id=order_id, amount=amount)
        return {
            "order_id": order_id,
            "payment_url": payment_url,
        }

    if order_id == -1:
        logger.error("Error while creating order: temporary_booking_id: %s, telegram_id: %s, location: %s",
                     temporary_booking_id, telegram_id, location)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "message": "Error in create invoice handler, cannot create"
            }
        )

    payment_url = await generate_payme_url(order_id=order_id, amount=amount)

    logger.info("Payme Create Invoice, created url -> order_id: %s, url: %s", temporary_booking_id, payment_url)

    return {
        "order_id":    order_id,
        "payment_url": payment_url,
    }


# @router.get("/{order_id}/status")
# async def check_order_status(order_id: str):
#     if order_id not in PAYMENT_CACHE:
#         status = await db.get_order_status(order_id=order_id)
#         if status == -1:
#             logger.exception("Order is not existed: %s", order_id)
#             return JSONResponse(
#                 status_code=404,
#                 content={"status": "order is not existed"}
#             )
#         PAYMENT_CACHE[order_id] = status
#
#     else:
#         status = PAYMENT_CACHE.get(order_id, "pending")
#
#     if status in ("paid", "cancelled"):
#         PAYMENT_CACHE.pop(order_id, None)
#
#     return {"status": status}


@router.get("/get_invoice_link/{order_id}")
async def get_existed_invoice_link(order_id: str):

    amount = await db.get_order_price(order_id=order_id)
    if amount == -1:
        return JSONResponse(
            status_code=404,
            content={"status": "order is not existed"}
        )

    if amount == -2:
        return JSONResponse(
            status_code=409,
            content={"status": "timeout is expired"}
        )

    price = amount / 100
    payment_url = await generate_payme_url(order_id=order_id, amount=amount)

    logger.info("Payme Create Invoice, created url -> order_id: %s, url: %s", order_id, payment_url)

    return {
        "order_id": order_id,
        "price": price,
        "payment_url": payment_url,
    }




