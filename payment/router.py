from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from payment.payme.router import router as payme_router
from database.database import db
from payment.click.router import router as click_router
import logging
from config.config import PAYMENT_CACHE

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/payments", tags=["Payment's router"])

router.include_router(payme_router, prefix="/payme", tags=["Payme"])
router.include_router(click_router, prefix="/click", tags=["Click"])


@router.get("/{order_id}/status")
async def check_order_status(order_id: str):
    if order_id not in PAYMENT_CACHE:
        status = await db.get_order_status(order_id=order_id)
        if status == -1:
            logger.exception("Order is not existed: %s", order_id)
            return JSONResponse(
                status_code=404,
                content={"status": "order is not existed"}
            )
        PAYMENT_CACHE[order_id] = status

    else:
        status = PAYMENT_CACHE.get(order_id, "pending")

    if status in ("paid", "cancelled"):
        PAYMENT_CACHE.pop(order_id, None)

    return {"status": status}



