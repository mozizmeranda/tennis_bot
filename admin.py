from aiogram import Router, F, Bot
from aiogram.types import CallbackQuery
from database import db
from google_calendar import create_booking_in_process
from keyboards import CalendarUtils


router = Router()

locs = {
    "A": "МГУ",
    "B": "Аджо"
}


@router.callback_query(F.data.startswith("admin_confirm_"))
async def admin_confirm(call: CallbackQuery, bot: Bot):
    print(call.data)
    screenshot = call.message.photo[-1].file_id
    text = call.message.caption
    lst = call.data.split("_")
    tg_id = lst[2]
    await call.message.edit_caption(caption=f"{text}\n\n----\n\nПодтверждено✅")
    await bot.send_message(chat_id=tg_id,
                           text=f"{text}\n\nПлатеж подтверждено администратором✅.\n Ждем вас у нас.😇",
                           reply_markup=CalendarUtils.main_menu())

    location = lst[3]
    date = lst[4]
    time_slot = lst[5]
    db.create_booking(tg_id, location, date, time_slot, screenshot)

    user = db.get_user_data_by_id(tg_id)
    create_booking_in_process(location, date, time_slot, user[0], user[1])


@router.callback_query(F.data.startswith("admin_cancel_"))
async def admin_confirm(call: CallbackQuery, bot: Bot):

    screenshot = call.message.photo[-1].file_id
    text = call.message.caption
    lst = call.data.split("_")
    tg_id = lst[2]

    number = db.get_number_by_id(tg_id)

    await call.message.edit_caption(caption=f"{text}\n\n----\n\nНомер телефона: {number}\n\nОтказано!❌")
    await bot.send_message(chat_id=tg_id,
                           text=f"{text}\n\nПлатеж не был подтвержден администратором.❌ \n"
                                f"В случае возникновения ошибок, обратитесь к админу: <b>@tennisplusss</b>",
                           parse_mode="HTML")

