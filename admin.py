from aiogram import Router, F, Bot
from aiogram.types import CallbackQuery, Message
from database import db
from google_calendar import create_booking_in_process
from keyboards import CalendarUtils, rs_confirm_keys
from states import Mailing
from aiogram.fsm.context import FSMContext
from aiogram.filters import Command


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
    msg_id = db.get_message_id(tg_id)
    print(msg_id)
    await bot.delete_message(chat_id=tg_id, message_id=msg_id[0])
    db.delete_message_id(tg_id)
    # db.delete_from_deletes_table(tg_id)

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


@router.message(Command("rs"))
async def rs_command(message: Message, state: FSMContext):
    await message.answer("Отправьте текст для рассылки")
    await state.set_state(Mailing.get_text)


@router.message(Mailing.get_text)
async def get_text_state(message: Message, state: FSMContext):
    await message.answer(f"Ваш текст: {message.html_text}", parse_mode="HTML", reply_markup=rs_confirm_keys)
    await state.set_state(Mailing.confirm_mailing)
    await state.update_data(selected_text=message.html_text)


@router.callback_query(F.data  == "rs_confirm", Mailing.confirm_mailing)
async def rs_confirm(call: CallbackQuery, state: FSMContext, bot: Bot):
    users = db.get_all_users()
    await call.answer("Рассылка началась", show_alert=True)
    selected_text = await state.get_value("selected_text")
    for user in users:
        await bot.send_message(chat_id=user[0], text=selected_text, parse_mode="HTML")
        await bot.send_message(chat_id=user[0], text="Выберите действие.", reply_markup=CalendarUtils.main_menu())


@router.callback_query(F.data == "rs_cancel", Mailing.confirm_mailing)
async def rs_cancel(call: CallbackQuery, state: FSMContext):
    await call.answer()
    await call.message.answer("Чтобы снова сделать рассылку, вызовите команду /rs")
