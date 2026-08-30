"""
utils.py — Генерация ссылки на оплату Payme.

В config/config.py нужна переменная:
    PAYME_MERCHANT_ID = "твой_merchant_id"  # из кабинета merchant.paycom.uz
"""

import base64
from config.config import PAYME_MERCHANT_ID
import asyncio

test = "https://checkout.test.paycom.uz/"
real = "https://checkout.paycom.uz/"


async def generate_payme_url(order_id: str, amount: int, redirect_url: str = None, lang: str = "ru") -> str:
    """
    Генерирует ссылку на оплату Payme.

    order_id     — id заказа из твоей БД
    amount       — сумма в тийинах (сум × 100)
    redirect_url — куда редиректить после оплаты (необязательно)
    lang         — язык интерфейса: ru | uz | en
    """
    params = f"m={PAYME_MERCHANT_ID};ac.order_id={order_id};a={amount};l={lang}"
    # print(PAYME_MERCHANT_ID)
    if redirect_url:
        params += f";c={redirect_url}"

    encoded = base64.b64encode(params.encode()).decode()
    return f"{test}{encoded}"


# print(asyncio.run(generate_pay_url(23211, 100000, "https://yandex.uz/")))

texts = {
    "location": {
        "ru": "Локация",
        "en": "Location",
        "uz": "Lokatsiya",
        "uz-cyr": "Локация"
    },
    "booking_date": {
        "ru": "Дата",
        "en": "Date",
        "uz": "Sana",
        "uz-cyr": "Сана"
    },
    "time_slots": {
        "ru": "Слоты",
        "en": "Slots",
        "uz": "Slotlar",
        "uz-cyr": "Слотлар"
    },
    "payment_confirmed": {
        "ru": "Платеж подтвержден✅.",
        "en": "Payment confirmed✅.",
        "uz": "To‘lov tasdiqlandi✅.",
        "uz-cyr": "Тўлов тасдиқланди✅."
    },
    "wait_us": {
        "ru": "Ждем вас у нас.😇",
        "en": "We are waiting for you.😇",
        "uz": "Sizni kutamiz.😇",
        "uz-cyr": "Сизни кутамиз.😇"
    },
    "phone_number": {
        "ru": "Номер телефона",
        "en": "Phone number",
        "uz": "Telefon raqam",
        "uz-cyr": "Телефон рақам"
    },
    "rejected": {
        "ru": "Отказано",
        "en": "Rejected",
        "uz": "Rad etildi",
        "uz-cyr": "Рад этилди"
    },
    "payment_rejected": {
        "ru": "Платеж не был подтвержден.",
        "en": "Payment was not approved.",
        "uz": "To‘lov tasdiqlanmadi.",
        "uz-cyr": "Тўлов тасдиқланмади."
    },
    "contact_admin": {
        "ru": "В случае ошибок, обратитесь к админу",
        "en": "If you have issues, contact admin",
        "uz": "Xatolik bo‘lsa, admin bilan bog‘laning",
        "uz-cyr": "Хатолик бўлса, админ билан боғланинг"
    }
}


def t(key: str, lang: str):
    return texts[key].get(lang, texts[key]["ru"])

