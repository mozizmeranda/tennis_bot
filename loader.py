from aiogram import Bot, Dispatcher, types, F
import asyncio
from aiogram.types import CallbackQuery
from aiogram.filters import Command
from database import db
from keyboards import res_keys
from keyboards import Calendar as CalendarUtils, registration_keyboard
from states import Booking, RegistrationStates
from admin import router as admin_router
from info import router as info_router
from aiogram.fsm.context import FSMContext
import logging
from config import token

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

bot = Bot(token=token)
dp = Dispatcher()
dp.include_router(admin_router)
dp.include_router(info_router)

locs = {
    "A": "МГУ",
    "B": "Аджо"
}

@dp.message(Command("start"))
async def get_start(message: types.Message, state: FSMContext):
    await state.set_state(RegistrationStates.waiting_phone)
    await message.answer("Пожалуйста отправьте номер телефона нажав на кнопку ниже⬇️ или напишите текстом",
                         reply_markup=registration_keyboard)


@dp.message(RegistrationStates.waiting_phone)
async def get_number(message: types.Message, state: FSMContext):
    if message.text or message.contact:
        number = message.text or message.contact.phone_number
        db.insert_into(message.from_user.id, message.from_user.full_name, message.from_user.username, number)
        greeting = """🎾 Добро пожаловать в систему бронирования теннисных кортов!

Здесь вы можете забронировать корт на удобное время.
У нас доступно 5 кортов в 2 локациях.

Выберите действие:"""
        await message.answer(greeting, reply_markup=res_keys)
        await state.clear()

    else:
        await message.answer("Я же написал, номере телефона!")


@dp.callback_query(F.data == "book_court")
async def get_start(callback: types.CallbackQuery, state: FSMContext):
    await state.set_state(Booking.location)
    await callback.message.edit_text(
        "📍 Выберите локацию для бронирования:",
        reply_markup=CalendarUtils.get_loc_keys()
    )


@dp.callback_query(F.data.startswith("location_"), Booking.location)
async def get_locations(callback: types.CallbackQuery, state: FSMContext):
    selected_location = callback.data.split("_")[1]
    await state.update_data(selected_location=selected_location)

    await callback.message.edit_text(
        f"📍 Выбрана локация: <b>{locs[selected_location]}</b>\n\n"
        f"📅 Теперь выберите дату:",
        parse_mode="HTML", reply_markup=CalendarUtils.get_date_keyboard(days_ahead=7)
    )

    await state.set_state(Booking.day)


@dp.callback_query(F.data.startswith("date_"), Booking.day)
async def date(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer("Пожалуйста подождите немного. Проводится поиск свободных кортов ☺️", show_alert=True)

    await callback.message.edit_text("Пожалуйста подождите :)")

    selected_date = callback.data.split("_")[1]

    selected_day = selected_date.split("-")
    year = int(selected_day[0])
    month = int(selected_day[1])
    day = int(selected_day[2])

    await state.update_data(selected_date=selected_date)
    selected_location = await state.get_value("selected_location")

    await state.set_state(Booking.time)

    await callback.message.edit_text(
        f"📍 Выбрана локация: <b>{locs[selected_location]}</b>\n"
        f"📅 Выбрана дата: <b>{selected_date}</b>\n⏳ Выберите время. Доступные время для бронирования:",
        parse_mode="HTML", reply_markup=CalendarUtils.get_time_free_slots(selected_location, year, month, day)
    )


@dp.callback_query(F.data.startswith("time_"), Booking.time)
async def time_slot(callback: types.CallbackQuery, state: FSMContext):
    selected_time = callback.data.split("_")[1]
    # print(selected_time)
    await state.update_data(selected_time=selected_time, telegram_id=callback.from_user.id)
    selected_location = await state.get_value("selected_location")
    selected_date = await state.get_value("selected_date")

    booking_info = (
        f"✅ <b>Бронирование создано!</b>\n\n"
        f"🏢 Локация: <b>{locs[selected_location]}</b>\n"
        f"📅 Дата: <b>{selected_date}</b>\n"
        f"⏰ Время: {selected_time}\n"
        f"💰 <b>Для завершения бронирования:</b>\n"
        f"Если все верно, нажмите кнопку 'Подтвердить'\n\n"
        f"Поспешите, корт могут забронить раньше вас."
    )

    booking_id = f"{callback.message.from_user.id}_{callback.data}"
    await callback.message.edit_text(
        booking_info,
        parse_mode="HTML", reply_markup=CalendarUtils.get_booking_confirmation_keyboard(booking_id)
    )


@dp.callback_query(F.data.startswith("confirm_booking_"))
async def confirm_key_clicked(call: CallbackQuery, state: FSMContext):
    await call.message.edit_text(
        "Отправьте скриншот транзакции. \n\nЧтобы поменять что-то вам нужно вернуться в главное меню.",
        reply_markup=CalendarUtils.get_cancel_keyboard()
    )
    await state.set_state(Booking.screenshot)


@dp.message(Booking.screenshot)
async def getting_screenshot(message: types.Message, state: FSMContext):
    screenshot = message.message_id

    if not message.photo:
        await message.answer("Отправьте пожалуйста фотографию вашей транзакции.\nСкриншот!")
        await bot.delete_message(message.from_user.id, message_id=screenshot)
        return

    data = await state.get_data()
    print(data)
    telegram_id = data.get('telegram_id')

    selected_date = data.get('selected_date')
    selected_time = data.get('selected_time')
    selected_location = data.get('selected_location')
    booking_info = f"{telegram_id}_{selected_location}_{selected_date}_{selected_time}"

    number = db.get_number_by_id(telegram_id)
    text = (
        f"✅ Бронирование создано!\n\n"
        f"📅 Дата: {selected_date}\n"
        f"⏰ Время: {selected_time}\n"
        f"🏢 Локация: {locs[selected_location]}\n"
        f"Номер: {number}"
    )

    await bot.send_photo(chat_id=827950639,
                         photo=message.photo[-1].file_id,
                         caption=text,
                         reply_markup=CalendarUtils.admin_keyboard(booking_info))

    await message.answer("Спасибо, дождитесь подтверждения администратора!😇\nВам придет "
                         "сообщщение, когда платеж будет одобрен", reply_markup=CalendarUtils.main_menu())
    await state.clear()


#-------------------------------------------------------------------------------------------------------
#-------------------------------------------------------------------------------------------------------
#-------------------------------------------------------------------------------------------------------
#-------------------------------------------------------------------------------------------------------
#-------------------------------------------------------------------------------------------------------
#-------------------------------------------------------------------------------------------------------
#-------------------------------------------------------------------------------------------------------
#-------------------------------------------------------------------------------------------------------
#-------------------------------------------------------------------------------------------------------
#-------------------------------------------------------------------------------------------------------
#-------------------------------------------------------------------------------------------------------


@dp.callback_query(F.data == "back_to_date")
async def main_menu(callback: types.CallbackQuery, state: FSMContext):
    """Возврат в панель с локациями"""
    selected_location = await state.get_value("selected_location")

    await state.set_state(Booking.day)

    await callback.message.edit_text(
        f"📍 Выбрана локация: {locs[selected_location]}\n\n"
        f"📅 Теперь выберите дату:",
        reply_markup=CalendarUtils.get_date_keyboard(days_ahead=7)
    )


@dp.callback_query(F.data == "back_to_location")
async def main_menu(callback: types.CallbackQuery, state: FSMContext):
    """Возврат в панель с локациями"""

    await state.set_state(Booking.location)

    await callback.message.edit_text(
        f"📍 Выберите локацию:",
        reply_markup=CalendarUtils.get_loc_keys()  # Ваша главная клавиатура
    )
    await callback.answer()


@dp.callback_query(F.data == "back_to_time")
async def main_menu(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer("Пожалуйста подождите немного. Проводится поиск свободных кортов ☺️", show_alert=True)
    selected_date = await state.get_value("selected_date")

    selected_day = selected_date.split("-")
    year = int(selected_day[0])
    month = int(selected_day[1])
    day = int(selected_day[2])

    await state.update_data(selected_date=selected_date)
    selected_location = await state.get_value("selected_location")

    await state.set_state(Booking.time)

    await callback.message.edit_text(
        f"📍 Выбрана локация: {locs[selected_location]}\n"
        f"📅 Выбрана дата: {selected_date}\n⏳ Выберите время. Доступные время для бронирования:",
        reply_markup=CalendarUtils.get_time_free_slots(selected_location, year, month, day)
    )


@dp.callback_query(F.data == "main_menu")
async def main_menu(callback: types.CallbackQuery, state: FSMContext):
    """Возврат в главное меню"""
    await state.clear()  # Очищаем состояние
    await callback.message.edit_text(
        "🏠 Главное меню\n\nВыберите действие:",
        reply_markup=res_keys  # Ваша главная клавиатура
    )
    await callback.answer()


@dp.callback_query(F.data == "cancel_booking")
async def cancel_booking(callback: types.CallbackQuery, state: FSMContext):
    """Отмена бронирования"""
    await state.clear()
    await callback.message.edit_text(
        "❌ Бронирование отменено.\n\n"
        "Выберите действие:",
        reply_markup=res_keys
    )
    await callback.answer("Бронирование отменено")


async def main():
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())





