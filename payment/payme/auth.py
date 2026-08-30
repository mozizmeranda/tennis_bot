"""
auth.py — Проверка Authorization заголовка от Payme.

В config/config.py нужны две переменные:
    PAYME_KEY       = "твой_секретный_ключ"   # Кабинет → Кассы → Ключ
    PAYME_LOGIN     = "Paycom"                 # всегда "Paycom", но вынесем в конфиг
"""

import base64
from fastapi import Request
from config.config import PAYME_KEY, PAYME_MERCHANT_ID
from .errors import error, AUTHORIZATION_FAILED


async def check_auth(request: Request, req_id) -> dict | None:
    """
    Проверяет заголовок Authorization.

    Возвращает None если всё ок.
    Возвращает dict с ошибкой если авторизация не прошла — его нужно сразу отдать Payme.
    """
    auth_header = request.headers.get("Authorization", "")

    if not auth_header.startswith("Basic "):
        return error(AUTHORIZATION_FAILED, "Недостаточно прав", req_id)

    try:
        decoded = base64.b64decode(auth_header[6:]).decode("utf-8")
        login, key = decoded.split(":", 1)

    except Exception:
        return error(AUTHORIZATION_FAILED, "Недостаточно прав", req_id)

    if login != PAYME_MERCHANT_ID or key != PAYME_KEY:
        return error(AUTHORIZATION_FAILED, "Недостаточно прав", req_id)

    return None
