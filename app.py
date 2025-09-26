from aiogram import Bot, Dispatcher, types, F
import asyncio
from aiogram.types import CallbackQuery
from aiogram.filters import Command
from database import db
from keyboards import res_keys
from keyboards import Calendar as CalendarUtils, registration_keyboard
from states import Booking, RegistrationStates
from aiogram.fsm.context import FSMContext
import logging
from config import token

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

bot = Bot(token=token)
dp = Dispatcher()


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


# @dp.message(Command("start"))
# async def get_start(message: types.Message):
#     db.insert_into(message.from_user.id, message.from_user.full_name, message.from_user.username)
#     greeting = """🎾 Добро пожаловать в систему бронирования теннисных кортов!
#
# Здесь вы можете забронировать корт на удобное время.
# У нас доступно 5 кортов в 2 локациях.
#
# Выберите действие:"""
#     await message.answer(greeting, reply_markup=res_keys)


@dp.callback_query(F.data == "info")
async def get_info(callback: types.CallbackQuery):
    await callback.message.answer("123")
    await callback.answer()  # Обязательно!


@dp.callback_query(F.data == "book_court")
async def get_info(callback: types.CallbackQuery, state: FSMContext):
    await state.set_state(Booking.day)
    await callback.message.edit_text(
        "📅 Выберите дату для бронирования:",
        reply_markup=CalendarUtils.get_date_keyboard(7)
    )


@dp.callback_query(F.data.startswith("date_"), Booking.day)
async def date_selected(callback: types.CallbackQuery, state: FSMContext):
    """Обработка выбора даты"""
    selected_date = callback.data.split("_", 1)[1]
    await state.update_data(selected_date=selected_date)

    await state.set_state(Booking.time)

    await callback.message.edit_text(
        f"📅 Выбрана дата: {selected_date}\n\n"
        f"⏰ Теперь выберите время:",
        reply_markup=CalendarUtils.get_time_slots_keyboard()
    )
    await callback.answer()


@dp.callback_query(F.data.startswith("time_"), Booking.time)
async def time_selected(callback: CallbackQuery, state: FSMContext):

    selected_time = callback.data.split("_", 1)[1]
    data = await state.get_data()
    selected_date = data['selected_date']

    await state.update_data(selected_time=selected_time)

    loc_a = "A"
    loc_b = "B"

    await state.set_state(Booking.location)

    await callback.message.edit_text(
        f"📅 Дата: {selected_date}\n"
        f"⏰ Время: {selected_time}\n\n"
        f"🏢 Выберите локацию:",
        reply_markup=CalendarUtils.get_locations_keyboard(selected_date, selected_time, loc_a, loc_b)
    )
    await callback.answer()


@dp.callback_query(F.data.startswith("location_"), Booking.location)
async def location_selected(callback: CallbackQuery, state: FSMContext):
    """Обработка выбора локации"""
    # Парсим данные: location_LocationName_date_time
    parts = callback.data.split("_")
    location = parts[1]
    selected_date = parts[2]
    selected_time = parts[3]

    data = await state.get_data()
    await state.update_data(selected_location=location)

    booked_courts = db.check_free_courts(selected_date, selected_time, location)
    # Получаем доступные корты
    court_keys, status = CalendarUtils.get_courts_keyboard(booked_courts, location, selected_date, selected_time)

    if status == 0:
        await callback.message.edit_text(
            f"😔 К сожалению, в локации {location} нет свободных кортов.\n\n"
            f"Попробуйте выбрать другую локацию или время.",
            reply_markup=court_keys
        )
        return

    await state.set_state(Booking.court)

    await callback.message.edit_text(
        f"📅 Дата: {selected_date}\n"
        f"⏰ Время: {selected_time}\n"
        f"🏢 Локация: {location}\n\n"
        f"🎾 Выберите корт:",
        reply_markup=court_keys
    )
    await callback.answer()


@dp.callback_query(F.data.startswith("court_"), Booking.court)
async def court_selected(callback: CallbackQuery, state: FSMContext):
    """Обработка выбора корта"""
    # Парсим данные: court_number_location_date_time
    print(callback.data)
    parts = callback.data.split("_")
    court_number = int(parts[1])
    location = parts[2]
    selected_date = parts[3]
    selected_time = parts[4]

    await state.update_data(
        selected_court=court_number,
        telegram_id=callback.from_user.id
    )

    # await state.set_state(booking)

    booking_info = (
        f"✅ **Бронирование создано!**\n\n"
        f"📅 Дата: {selected_date}\n"
        f"⏰ Время: {selected_time}\n"
        f"🏢 Локация: {location}\n"
        f"🎾 Корт: {court_number}\n\n"
        f"💰 **Для завершения бронирования:**\n"
        f"Если все верно, нажмите кнопку 'Подтвердить'\n\n"
        f"Поспешите, корт могут забронить раньше вас."
    )
    booking_id = f"{callback.message.from_user.id}_{callback.data}"
    await callback.message.edit_text(
        booking_info,
        parse_mode="Markdown", reply_markup=CalendarUtils.get_booking_confirmation_keyboard(booking_id)
    )
    await callback.answer("Бронирование создано! Отправьте скриншот оплаты.")


@dp.callback_query(F.data.startswith("confirm_booking_"))
async def confirm_key_clicked(call: CallbackQuery, state: FSMContext):
    await call.message.edit_text(
        "Отправьте скриншот транзакции. \n\nЧтобы поменять что-то вам нужно вернуться в главное меню.",
        reply_markup=CalendarUtils.get_cancel_keyboard()
    )
    await state.set_state(Booking.screenshot)


@dp.message(Booking.screenshot)
async def get_screenshot(message: types.Message, state: FSMContext):
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
    selected_court = data.get('selected_court')
    selected_location = data.get('selected_location')
    booking_info = f"{telegram_id}_{selected_court}_{selected_location}_{selected_date}_{selected_time}"

    number = db.get_number_by_id(telegram_id)
    text = (
        f"✅ **Бронирование создано!**\n\n"
        f"📅 Дата: {selected_date}\n"
        f"⏰ Время: {selected_time}\n"
        f"🏢 Локация: {selected_location}\n"
        f"🎾 Корт: {selected_court}\n\n"
        f"Номер: {number}"
    )

    await bot.send_photo(chat_id=827950639,
                         photo=message.photo[-1].file_id,
                         caption=text,
                         reply_markup=CalendarUtils.admin_keyboard(booking_info))

    await message.answer("Спасибо, дождитесь подтверждения администратора!😇")


@dp.callback_query(F.data.startswith("admin_confirm_"))
async def admin_confirm(call: CallbackQuery):
    print(call.data)
    screenshot = call.message.photo[-1].file_id
    text = call.message.caption
    lst = call.data.split("_")
    tg_id = lst[2]
    await call.message.edit_caption(caption=f"{text}\n\n----\n\nПодтверждено✅")
    await bot.send_message(chat_id=tg_id,
                           text=f"{text}\n\nПлатеж подтверждено администратором✅.\n Ждем вас у нас.😇")

    court_number = lst[3]
    location = lst[4]
    date = lst[5]
    time_slot = lst[6]
    db.create_booking(tg_id, court_number, location, date, time_slot, screenshot)


# ----------------------------------------------------------------------------------------------------- begin

@dp.callback_query(F.data == "back_to_date")
async def back_to_date(callback: types.CallbackQuery, state: FSMContext):
    """Возврат к выбору даты"""
    await state.set_state(Booking.day)
    await callback.message.edit_text(
        "📅 Выберите дату для бронирования:",
        reply_markup=CalendarUtils.get_date_keyboard(days_ahead=7)
    )
    await callback.answer()


@dp.callback_query(F.data == "back_to_time")
async def back_to_time(callback: types.CallbackQuery, state: FSMContext):
    """Возврат к выбору времени"""
    data = await state.get_data()
    selected_date = data.get('selected_date', 'не выбрана')

    await state.set_state(Booking.time)
    await callback.message.edit_text(
        f"📅 Дата: {selected_date}\n⏰ Выберите время:",
        reply_markup=CalendarUtils.get_time_slots_keyboard()
    )
    await callback.answer()


@dp.callback_query(F.data == "back_to_location")
async def back_to_location(callback: types.CallbackQuery, state: FSMContext):
    """Возврат к выбору локации"""
    data = await state.get_data()
    selected_date = data.get('selected_date')
    selected_time = data.get('selected_time')

    loc_a = "A"
    loc_b = "B"

    await state.set_state(Booking.location)

    await callback.message.edit_text(
        f"📅 Дата: {selected_date}\n"
        f"⏰ Время: {selected_time}\n\n"
        f"🏢 Выберите локацию:",
        reply_markup=CalendarUtils.get_locations_keyboard(selected_date, selected_time, loc_a, loc_b)
    )
    await callback.answer()


@dp.callback_query(F.data == "back_to_court")
async def back_to_court(callback: types.CallbackQuery, state: FSMContext):
    """Возврат к выбору корта"""
    data = await state.get_data()
    selected_date = data.get('selected_date')
    selected_time = data.get('selected_time')
    selected_location = data.get('selected_location')

    # Получаем доступные корты заново
    booked_courts = db.check_free_courts(selected_date, selected_time, selected_location)
    # Получаем доступные корты
    court_keys, status = CalendarUtils.get_courts_keyboard(booked_courts, selected_location, selected_date, selected_time)

    await state.set_state(Booking.court)
    await callback.message.edit_text(
        f"📅 Дата: {selected_date}\n"
        f"⏰ Время: {selected_time}\n"
        f"🏢 Локация: {selected_location}\n\n"
        f"🎾 Выберите корт:",
        reply_markup=court_keys
    )
#     await callback.answer()


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

# -----------------------------------------------------------------------------------------------------


async def main():
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())

