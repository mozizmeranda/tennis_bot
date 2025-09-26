# navigation.py
from aiogram import F, types
from aiogram.fsm.context import FSMContext
from states.booking import BookingStates
from utils.calendar import CalendarUtils
from database.models import Database


class NavigationHandlers:
    """Класс для обработки навигации "Назад" """

    @staticmethod
    async def back_to_date(callback: types.CallbackQuery, state: FSMContext):
        """Возврат к выбору даты"""
        await state.set_state(BookingStates.date)
        await callback.message.edit_text(
            "📅 Выберите дату для бронирования:",
            reply_markup=CalendarUtils.get_date_keyboard(config.BOOKING_DAYS_AHEAD)
        )
        await callback.answer()

    @staticmethod
    async def back_to_time(callback: types.CallbackQuery, state: FSMContext):
        """Возврат к выбору времени"""
        data = await state.get_data()
        selected_date = data.get('selected_date', 'не выбрана')

        await state.set_state(BookingStates.time)
        await callback.message.edit_text(
            f"📅 Дата: {selected_date}\n⏰ Выберите время:",
            reply_markup=CalendarUtils.get_time_slots_keyboard()
        )
        await callback.answer()

    @staticmethod
    async def back_to_location(callback: types.CallbackQuery, state: FSMContext, db: Database):
        """Возврат к выбору локации"""
        data = await state.get_data()
        selected_date = data.get('selected_date')
        selected_time = data.get('selected_time')

        # Проверяем доступные локации заново
        available_locations = []
        for location in config.LOCATIONS:
            available_courts = await db.get_available_courts(location, selected_date, selected_time)
            if available_courts:
                available_locations.append(location)

        await state.set_state(BookingStates.location)
        await callback.message.edit_text(
            f"📅 Дата: {selected_date}\n"
            f"⏰ Время: {selected_time}\n\n"
            f"🏢 Выберите локацию:",
            reply_markup=CalendarUtils.get_locations_keyboard(selected_date, selected_time, available_locations)
        )
        await callback.answer()

    @staticmethod
    async def back_to_court(callback: types.CallbackQuery, state: FSMContext, db: Database):
        """Возврат к выбору корта"""
        data = await state.get_data()
        selected_date = data.get('selected_date')
        selected_time = data.get('selected_time')
        selected_location = data.get('selected_location')

        # Получаем доступные корты заново
        available_courts = await db.get_available_courts(selected_location, selected_date, selected_time)

        await state.set_state(BookingStates.court)
        await callback.message.edit_text(
            f"📅 Дата: {selected_date}\n"
            f"⏰ Время: {selected_time}\n"
            f"🏢 Локация: {selected_location}\n\n"
            f"🎾 Выберите корт:",
            reply_markup=CalendarUtils.get_courts_keyboard(available_courts, selected_location, selected_date,
                                                           selected_time)
        )
        await callback.answer()

    @staticmethod
    async def main_menu(callback: types.CallbackQuery, state: FSMContext):
        """Возврат в главное меню"""
        from keyboards.inline import get_main_menu_keyboard

        await state.clear()  # Очищаем состояние
        await callback.message.edit_text(
            "🏠 Главное меню\n\nВыберите действие:",
            reply_markup=get_main_menu_keyboard()
        )
        await callback.answer()

    @staticmethod
    async def cancel_booking(callback: types.CallbackQuery, state: FSMContext):
        """Отмена бронирования"""
        from keyboards.inline import get_main_menu_keyboard

        await state.clear()
        await callback.message.edit_text(
            "❌ Бронирование отменено.\n\n"
            "Выберите действие:",
            reply_markup=get_main_menu_keyboard()
        )
        await callback.answer("Бронирование отменено")


def register_navigation_handlers(router):
    """Регистрация всех навигационных обработчиков"""

    @router.callback_query(F.data == "back_to_date")
    async def back_to_date_handler(callback: types.CallbackQuery, state: FSMContext):
        await NavigationHandlers.back_to_date(callback, state)

    @router.callback_query(F.data == "back_to_time")
    async def back_to_time_handler(callback: types.CallbackQuery, state: FSMContext):
        await NavigationHandlers.back_to_time(callback, state)

    @router.callback_query(F.data == "back_to_location")
    async def back_to_location_handler(callback: types.CallbackQuery, state: FSMContext, db: Database):
        await NavigationHandlers.back_to_location(callback, state, db)

    @router.callback_query(F.data == "back_to_court")
    async def back_to_court_handler(callback: types.CallbackQuery, state: FSMContext, db: Database):
        await NavigationHandlers.back_to_court(callback, state, db)

    @router.callback_query(F.data == "main_menu")
    async def main_menu_handler(callback: types.CallbackQuery, state: FSMContext):
        await NavigationHandlers.main_menu(callback, state)

    @router.callback_query(F.data == "cancel_booking")
    async def cancel_booking_handler(callback: types.CallbackQuery, state: FSMContext):
        await NavigationHandlers.cancel_booking(callback, state)
