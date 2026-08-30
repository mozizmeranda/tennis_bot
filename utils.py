from httpx import AsyncClient
from config.config import *
import base64
from nanoid import generate
import logging
from network.client import get_http_client


logger = logging.getLogger(__name__)


async def send_check_to_admin(client: AsyncClient, photo_bytes, filename, content_type, caption, reply_markup):
    try:
        url = f'https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendPhoto'
        response = await client.post(
            url,
            data={
                'chat_id': ADMIN_ID,
                'caption': caption,
                'reply_markup': reply_markup
            },
            files={'photo': (filename, photo_bytes, content_type)},
            timeout=60
        )
        response.json()
        return 1

    except Exception as exp:
        print(f"Error while sending photo to admin from\n {caption}")
        return 0


async def notify_admin(func_name: str, error: str, arguments=None):
    if arguments is None:
        arguments = {"00": 00}
    try:
        url = f'https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage'
        text = (f"Func name:\n ```{func_name}``` \n\nError:\n ```{error}```  \n "
                f"Arguments:\n ```{arguments.items() if arguments else "Nothing"}```\n")
        response = await get_http_client().post(
            url,
            data={
                'chat_id': ADMIN_ID,
                'text': text,
                'parse_mode': 'MarkdownV2'
            },
            timeout=60
        )
        response.json()

    except Exception as exp:
        logger.error("Error in notify admin: %s", exp)

# auth_header = "Basic UGF5Y29tOlV6Y2FyZDpzb21lUmFuZG9tU3RyaW5nMTU0NTM0MzU0MzU0NQ=="
#
# # 1. Отсекаем слово "Basic "
# encoded_credentials = auth_header.split(" ")[1] # Получим "dXNlcjEyMzpwYXNzNDU2"
#
# # 2. Декодируем из Base64 в байты, а затем в строку
# decoded_bytes = base64.b64decode(encoded_credentials)
# decoded_str = decoded_bytes.decode("utf-8") # Получим "user123:pass456"
# print(decoded_str)
#
# # 3. Разделяем по двоеточию
# merchant_id, secret_key = decoded_str.split(":", 1)
#
# print(f"Merchant ID: {merchant_id}")
# print(f"Secret Key: {secret_key}")

# Задаем надежный алфавит без путающих символов (опционально)
alphabet = '0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz'


def nanoid_generate():
    return generate(alphabet, 8)
#
# import base64
#
# # Ваша строка из заголовка
# auth_header = "Basic UGF5Y29tOmhoMVpuUzNpNlRZMFV3WkZqVUFWb3lQSXh4dnVnUE5xI3BGOA=="
# # auth_header = "Basic UGF5Y29tOlV6Y2FyZDpzb21lUmFuZG9tU3RyaW5nMTU0NTM0MzU0MzU0NQ=="
# # 1. Отрезаем "Basic " (первые 6 символов)
# encoded_data = auth_header[6:]
#
# # 2. Декодируем из base64 в байты, а затем в строку utf-8
# decoded_str = base64.b64decode(encoded_data).decode("utf-8")
#
# # 3. Разделяем логин и пароль по первому двоеточию
# login, password = decoded_str.split(":", 1)
#
# print(f"Логин: {login}")
# print(f"Пароль: {password}")

