# app.py
import logging
import traceback

from config import config, models
from contextlib import asynccontextmanager
from fastapi import FastAPI, status, UploadFile, File, Form, Body
from fastapi.responses import JSONResponse
import json
import uvicorn
from network.client import manager, get_http_client
import httpx
from payment.router import router

from profile.profile_endpoint import profile_router

from google.google_config import gc_instance, load_service_account_data
from google.services import returning_free_slots
from fastapi import Request
from datetime import datetime, timedelta
from telegram_bot.bot_app import dp, bot, bot_router
from database.database import db
from typing import Dict, Any
from utils import send_check_to_admin, nanoid_generate, notify_admin
import uuid

from calendar_api.calendar import router as calendar_router
from calendar_api.event import router as event_router

from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.middleware import SlowAPIMiddleware
from slowapi.errors import RateLimitExceeded
from slowapi import _rate_limit_exceeded_handler


def short_uuid():
    return str(uuid.uuid4()).replace('-', '')[:8]


@asynccontextmanager
async def lifespan(app: FastAPI):
    # ---- КОД ВЫПОЛНЯЕТСЯ РОВНО ОДИН РАЗ ПРИ СТАРТЕ СЕРВЕРА ----
    manager.api_client = httpx.AsyncClient(
        timeout=httpx.Timeout(10.0, connect=5.0),
        limits=httpx.Limits(max_connections=100, max_keepalive_connections=20)
    )
    logger.info("Запуск приложения: загружаем сервисный аккаунт Google...")
    load_service_account_data(gc_instance)
    await db.connect()

    if config.WEBHOOK_URL:
        # Устанавливаем URL и секретный токен
        await bot.set_webhook(
            url=config.WEBHOOK_URL,
            secret_token=config.WEBHOOK_SECRET,
            drop_pending_updates=True  # Сбрасывает зависшие апдейты, накопленные во время оффлайна
        )
        logging.info(f"Вебхук успешно установлен на {config.WEBHOOK_URL}")

    yield

    try:
        await bot.delete_webhook()
        logger.info("Вебхук успешно удален.")
    except Exception as e:
        await notify_admin("Lifespan", str(traceback.format_exc()), arguments={})
        logger.info(f"Ошибка при удалении вебхука: {e}")

        # Закрываем сессию бота
    await bot.session.close()

    if manager.api_client:
        await manager.api_client.aclose()
        logger.info("HTTP-клиент успешно закрыт.")

    if db:
        await db.close()
        logger.info("Соединение с базой данных успешно закрыто.")

    logger.info("Остановка приложения...")


# app = FastAPI(lifespan=lifespan)
# limiter = Limiter(key_func=get_remote_address)

limiter = Limiter(key_func=get_remote_address)
app = FastAPI(lifespan=lifespan)
app.include_router(router)
app.include_router(profile_router)
app.include_router(bot_router)
app.include_router(calendar_router)
app.include_router(event_router)

app.state.limiter = limiter
app.add_exception_handler(
    RateLimitExceeded,
    _rate_limit_exceeded_handler
)

app.add_middleware(SlowAPIMiddleware)
logger = logging.getLogger(__name__)
logger.info("Логгер успешно запущен")


@app.post("/free-slots")
@limiter.limit("5/minute")
async def free_slots_endpoint(request: Request, payload: Dict[str, Any]):
    logger.info("Request body:\n%s", json.dumps(payload, ensure_ascii=False, indent=2))
    location = payload.get("location", "")
    if not location:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"message": "Недостаточно параметров для получения информации"}
        )

    # Приводим к int с обработкой ошибок
    try:
        year = int(payload.get("year", 2026))
        month = int(payload.get("month", 0))
        day = int(payload.get("day", 0))
    except (ValueError, TypeError):
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"message": "Параметры year, month и day должны быть числами"}
        )

    try:
        # Передаем уже гарантированно числовые параметры
        result = await returning_free_slots(
            client=get_http_client(),
            gc=gc_instance,
            location=location,
            year=year,
            month=month,
            day=day
        )

        return JSONResponse(status_code=status.HTTP_200_OK, content=result)

    except Exception as e:
        logger.error(msg=str(e))
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"message": f"Внутренняя ошибка сервера: {str(e)}"}
        )


@app.post("/language")
async def get_language_handler(data: Dict[str, Any] = Body(...)):
    if not data or 'id' not in data:
        return JSONResponse(status_code=400, content={"error": "id is required"})

    user_id = data['id']
    lang = await db.get_user_language(user_id)

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={"id": user_id, "language": lang}
    )


@app.post("/get-price")
async def get_price_handler(data: Dict[str, Any] = Body(...)):
    try:
        if not data or 'location' not in data or 'time_slot' not in data:
            return JSONResponse(status_code=400, content={"error": "location and time_slot required"})

        location = data['location']
        time_slot = data['time_slot']

        price = await db.get_price(location, time_slot)

        if price is None:
            return JSONResponse(status_code=404, content={"error": "price not found"})

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "location": location,
                "time_slot": time_slot,
                "price": price
            }
        )
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})


@app.post("/update-price")
async def update_price_handler(data: Dict[str, Any] = Body(...)):
    try:
        if not data or 'location' not in data or 'time_slot' not in data or 'price' not in data:
            return JSONResponse(status_code=400, content={"error": "location, time_slot and price required"})

        location = data['location']
        time_slot = data['time_slot']
        price = data['price']

        await db.update_price(location, time_slot, price)

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "status": "updated",
                "location": location,
                "time_slot": time_slot,
                "price": price
            }
        )
    except Exception as e:
        logger.exception("Error while changing price: %s", )
        return JSONResponse(status_code=500, content={"error": str(e)})


@app.post("/change-language")
async def change_language_handler(data: Dict[str, Any] = Body(...)):
    try:
        if not data or 'id' not in data or 'language' not in data:
            return JSONResponse(status_code=400, content={"error": "id and language are required"})

        user_id = data['id']
        new_language = data['language']

        await db.update_user_language(user_id, new_language)

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "status": "updated",
                "id": user_id,
                "language": new_language
            }
        )
    except Exception as e:
        print("ERROR:", e)
        return JSONResponse(status_code=500, content={"error": str(e)})


@app.post("/get-full-price")
async def get_full_price_handler(body: models.GetFullPriceBody):
    logger.info("[get-full-price] Incoming body: %s", body.model_dump_json(indent=2))
    try:
        free_courts_quantity = body.free_courts_quantity
        location = body.location
        booking_date = body.day
        telegram_id = body.telegram_id
        time_slots = body.time_slots

        if not all([location, booking_date, telegram_id, time_slots]):
            return JSONResponse(status_code=400, content={"error": "Missing required fields"})

        first = time_slots[0]
        last = time_slots[-1]
        summary_time_slot = f"{first[:5]}-{last[6:]}"

        # Вызываем асинхронную пачку цен
        prices = await db.get_prices_bulk(location, time_slots)
        total_price = sum(prices)

        expires_at = (datetime.now() + timedelta(minutes=4)).strftime('%Y-%m-%d %H:%M:%S')
        temporary_order_id = nanoid_generate()

        # Записываем холды в базу по очереди
        for slot in time_slots:
            db_resp = await db.create_pending(free_courts_quantity, temporary_order_id, location, booking_date, slot,
                                              telegram_id, expires_at)
            if db_resp == 0:
                logger.exception("Order is not created: order_id: %s, telegram_id: %s", temporary_order_id, telegram_id)
                await notify_admin(get_full_price_handler.__name__, "Order is not created: order_id",
                                   {"order_id": temporary_order_id, "telegram_id": telegram_id})

                return JSONResponse(
                    status_code=status.HTTP_409_CONFLICT,
                    content={
                        "message": "Слоты уже успели занять к сожалению...."
                    }
                )

        logger.info("Order created: order_id: %s, telegram_id: %s", temporary_order_id, telegram_id)
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "temprary_order_id": temporary_order_id,
                "location": location,
                "time_slot": summary_time_slot,
                "price": total_price
            }
        )

    except Exception as e:
        logger.error(msg=e)
        await notify_admin(get_full_price_handler.__name__, error=str(traceback.format_exc()), arguments=dict(body))
        return JSONResponse(status_code=500, content={"error": str(e)})


@app.get("/ping")
async def ping_endpoint():
    """
    Простой проверочный эндпоинт (Health Check).
    Используется для проверки работоспособности сервера и мониторинга (например, UptimeRobot).
    """
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={"status": "healthy", "message": "pong"}
    )


if __name__ == "__main__":
    uvicorn.run("app:app", host="localhost", port=8080, reload=True, log_level="warning")
