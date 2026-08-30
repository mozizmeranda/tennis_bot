# from aiogram import Router, F, Bot
# from aiogram.types import CallbackQuery, Message
# from database.database import db
# from .keyboards import rs_confirm_keys
# from .states import Mailing
# from aiogram.fsm.context import FSMContext
# from aiogram.filters import Command
# from google.google_config import get_google_config
# from google.services import google_create_booking
# from network.client import get_http_client
# router = Router()
#
# # locs = {
# #     "A": "МГУ",
# #     "B": "Аджо"
# # }
#
#
# texts = {
#     "approved_admin": {
#         "ru": "Подтверждено✅",
#         "en": "Approved by admin✅",
#         "uz": "Admin tomonidan tasdiqlandi✅",
#         "uz-cyr": "Админ томонидан тасдиқланди✅"
#     },
#     "payment_confirmed": {
#         "ru": "Платеж подтвержден администратором✅.",
#         "en": "Payment confirmed by admin✅.",
#         "uz": "To‘lov admin tomonidan tasdiqlandi✅.",
#         "uz-cyr": "Тўлов админ томонидан тасдиқланди✅."
#     },
#     "wait_us": {
#         "ru": "Ждем вас у нас.😇",
#         "en": "We are waiting for you.😇",
#         "uz": "Sizni kutamiz.😇",
#         "uz-cyr": "Сизни кутамиз.😇"
#     },
#     "phone_number": {
#         "ru": "Номер телефона",
#         "en": "Phone number",
#         "uz": "Telefon raqam",
#         "uz-cyr": "Телефон рақам"
#     },
#     "rejected": {
#         "ru": "Отказано",
#         "en": "Rejected",
#         "uz": "Rad etildi",
#         "uz-cyr": "Рад этилди"
#     },
#     "payment_rejected": {
#         "ru": "Платеж не был подтвержден администратором.",
#         "en": "Payment was not approved by admin.",
#         "uz": "To‘lov admin tomonidan tasdiqlanmadi.",
#         "uz-cyr": "Тўлов админ томонидан тасдиқланмади."
#     },
#     "contact_admin": {
#         "ru": "В случае ошибок, обратитесь к админу",
#         "en": "If you have issues, contact admin",
#         "uz": "Xatolik bo‘lsa, admin bilan bog‘laning",
#         "uz-cyr": "Хатолик бўлса, админ билан боғланинг"
#     }
# }
#
#
# def t(key: str, lang: str):
#     return texts[key].get(lang, texts[key]["ru"])
#
#
# @router.callback_query(F.data.startswith("adm_ok_"))
# async def admin_confirm(call: CallbackQuery, bot: Bot):
#
#     screenshot = call.message.photo[-1].file_id
#     text = call.message.caption
#     lst = call.data.split("_")
#     username = call.message.from_user.username
#
#     booking_id = lst[2]
#     booking_data = db.get_by_booking_id(booking_id)
#     print(booking_data)
#     tg_id = booking_data[0][4]
#
#     location = booking_data[0][1]
#     date = booking_data[0][2]
#     # time_slot = booking_data[3]
#     await call.message.answer(str(booking_data))
#     lang = db.get_lang(tg_id)
#
#     msg = await call.message.edit_caption(
#         caption=f"{text}\n\n----\n\n{t('approved_admin', lang)}"
#     )
#
#     await bot.send_message(
#         chat_id=tg_id,
#         text=f"{text}\n\n{t('payment_confirmed', lang)}\n{t('wait_us', lang)}\n{msg.get_url()}"
#     )
#
#     await db.kill_from_pending_bookings(booking_id)
#     # user = await db.get_user_data_by_id(tg_id)
#
#     user = await db.get_user_data_by_id(tg_id)
#     for rec in booking_data:
#         await google_create_booking(client=get_http_client(), gc=get_google_config(),
#                                     location=location, booking_date=date, time_slot=rec[3],
#                                     number=user[0], name=user[1])
#         await db.create_booking(tg_id, location, date, rec[3], screenshot)
#
#
# @router.callback_query(F.data.startswith("adm_no_"))
# async def admin_confirm(call: CallbackQuery, bot: Bot):
#
#     await call.answer(text="Вы не админ!", show_alert=True)
#     screenshot = call.message.photo[-1].file_id
#     text = call.message.caption
#     lst = call.data.split("_")
#
#     booking_id = lst[2]
#     booking_data = db.get_by_booking_id(booking_id)
#     print(booking_data)
#     tg_id = booking_data[0][4]
#
#     location = booking_data[0][1]
#     date = booking_data[0][2]
#     # time_slot = booking_data[3]
#
#     lang = db.get_lang(tg_id)
#
#     number = db.get_number_by_id(tg_id)
#
#     # db.kill_pending(location, date, time_slot)
#     await db.kill_from_pending_bookings(booking_id)
#
#     await call.message.edit_caption(
#         caption=f"{text}\n\n----\n\n{t('phone_number', lang)}: {number}\n\n{t('rejected', lang)}❌"
#     )
#
#     await bot.send_message(
#         chat_id=tg_id,
#         text=(
#             f"{text}\n\n"
#             f"{t('payment_rejected', lang)}❌\n"
#             f"{t('contact_admin', lang)}: <b>@tennisplusss</b>"
#         ),
#         parse_mode="HTML"
#     )
#
#
# @router.message(Command("rs"))
# async def rs_command(message: Message, state: FSMContext):
#     await message.answer("Отправьте текст для рассылки")
#     await state.set_state(Mailing.get_text)
#
#
# @router.message(Mailing.get_text)
# async def get_text_state(message: Message, state: FSMContext):
#     await message.answer(f"Ваш текст: {message.html_text}", parse_mode="HTML", reply_markup=rs_confirm_keys)
#     await state.set_state(Mailing.confirm_mailing)
#     await state.update_data(selected_text=message.html_text)
#
#
# @router.callback_query(F.data == "rs_confirm", Mailing.confirm_mailing)
# async def rs_confirm(call: CallbackQuery, state: FSMContext, bot: Bot):
#     users = db.get_all_users()
#     await call.answer("Рассылка началась", show_alert=True)
#     selected_text = await state.get_value("selected_text")
#     for user in users:
#         await bot.send_message(chat_id=user[0], text=selected_text, parse_mode="HTML")
#
#
# @router.callback_query(F.data == "rs_cancel", Mailing.confirm_mailing)
# async def rs_cancel(call: CallbackQuery, state: FSMContext):
#     await call.answer()
#     await call.message.answer("Чтобы снова сделать рассылку, вызовите команду /rs")
#     await state.clear()
