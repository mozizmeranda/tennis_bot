from fastapi import APIRouter, Request, status
from fastapi.responses import JSONResponse
from utils import notify_admin
from config.models import CreateInvoiceRequest
from database.database import db


profile_router = APIRouter(prefix="/profile", tags=["Profile"])


@profile_router.get("/{telegram_id}")
async def get_profile(telegram_id: int):

    rows = await db.get_profile_info(telegram_id=telegram_id)
    if rows == -1:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"error": "Пользователь не найден"}
        )

    return JSONResponse(status_code=status.HTTP_200_OK, content=rows)


@profile_router.get("/{telegram_id}/pendings")
async def get_profile(telegram_id: int):

    rows = await db.invoices(telegram_id=telegram_id, invoice_type="pendings")
    if rows == -1:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"error": "Броней не найдено"}
        )

    return JSONResponse(status_code=status.HTTP_200_OK, content=rows)


@profile_router.get("/{telegram_id}/paids_cancels")
async def get_profile(telegram_id: int):

    rows = await db.invoices(telegram_id=telegram_id, invoice_type="paids_cancels")
    if rows == -1:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"error": "Броней не найдено"}
        )

    return JSONResponse(status_code=status.HTTP_200_OK, content=rows)





