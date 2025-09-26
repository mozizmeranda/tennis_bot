from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from app import bot


router = Router()


@router.message()
async def send_screenshot_to_admin(message: Message):
    if message.photo:
        await bot.send_photo(chat_id=12, photo=message.photo[-1].file_id,
                             caption="")
