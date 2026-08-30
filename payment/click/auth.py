"""
Проверка MD5-подписи входящих запросов от Click.uz.
"""

import hashlib
from config.config import CLICK_SECRET_KEY


def _build_sign_string(data: dict) -> str:
    """
    Формирует строку для подписи согласно документации Click.

    Prepare (action=0):
        click_trans_id + service_id + secret_key + merchant_trans_id
        + amount + action + sign_time

    Complete (action=1):
        click_trans_id + service_id + secret_key + merchant_trans_id
        + merchant_prepare_id + amount + action + sign_time
    """
    action = int(data["action"])

    if action == 0:  # Prepare
        parts = [
            str(data["click_trans_id"]),
            str(data["service_id"]),
            CLICK_SECRET_KEY,
            str(data["merchant_trans_id"]),
            str(data["amount"]),
            str(data["action"]),
            str(data["sign_time"]),
        ]
    else:  # Complete
        parts = [
            str(data["click_trans_id"]),
            str(data["service_id"]),
            CLICK_SECRET_KEY,
            str(data["merchant_trans_id"]),
            str(data["merchant_prepare_id"]),
            str(data["amount"]),
            str(data["action"]),
            str(data["sign_time"]),
        ]

    return "".join(parts)


def verify_sign(data: dict) -> bool:
    """
    Возвращает True если подпись совпадает, иначе False.
    """
    sign_string = _build_sign_string(data)
    expected = hashlib.md5(sign_string.encode("utf-8")).hexdigest()
    return expected == data.get("sign_string", "")
