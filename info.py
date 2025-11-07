from aiogram import Router, F, Bot
from aiogram.types import CallbackQuery
from keyboards import CalendarUtils
from database import db

router = Router()
locs = {
    "A": "МГУ",
    "B": "Аджо"
}


@router.callback_query(F.data == "info")
async def get_info_keys(call: CallbackQuery):
    await call.message.edit_text(
        "Выберите корт, про который вы хотите узнать", reply_markup=CalendarUtils.get_info()
    )


@router.callback_query(F.data == "MSU")
async def msu_info(call: CallbackQuery):
    t = """
    🎾 <b>Открытый теннисный центр</b>

Второй филиал нашей школы — это отличное место для занятий на свежем воздухе:
 • 3 грунтовых корта с идеально ровным покрытием
 • Профессиональное освещение, позволяющее тренироваться даже вечером
 • Атмосфера большого тенниса под открытым небом

🔥 Подходит для игроков любого уровня: от детей до взрослых, от любителей до спортсменов.

📍 <b>Адрес</b>: МГУ Ломоносова, проспект Амир Темура, 19."""

    await call.message.edit_text(text=t, reply_markup=CalendarUtils.info_keys(), parse_mode="HTML")


@router.callback_query(F.data == "ajou")
async def msu_info(call: CallbackQuery):
    t = """
    🎾 <b>Крытый теннисный центр</b>

Наш крытый филиал — это идеальные условия для тренировок в любое время года:
 • 2 просторных корта с профессиональным покрытием хард
 • Современная система кондиционирования летом
 • Эффективное отопление зимой
 • Ровная поверхность и яркое место освещение, отвечающее стандартам турниров

🔥 Здесь всегда комфортная температура и отличные условия как для начинающих, так и для продвинутых игроков.

📍 <b>Адрес: Яшнободский район, Асалабад, 112. Университет Ajou.</b>"""

    await call.message.edit_text(text=t, reply_markup=CalendarUtils.info_keys(), parse_mode="HTML")


@router.callback_query(F.data == "back_to_info")
async def get_back_to_info(call: CallbackQuery):
    await call.message.edit_text(
        "Выберите корт, про который вы хотите узнать", reply_markup=CalendarUtils.get_info()
    )


@router.callback_query(F.data == "my_bookings")
async def my_bookings(call: CallbackQuery):
    print(call.from_user.id)
    all_bookings = db.get_all_bookings(call.from_user.id)
    print(all_bookings)
    t = ""
    for boooking in all_bookings:
        t += f"<b>Локация:</b> {locs[boooking[1]]}\n<b>Дата</b>: {boooking[2]}\n<b>Время</b>: {boooking[3]}\n\n"

    text = f"<b>Ваши бронирования:</b>\n\n{t}"

    await call.message.edit_text(
        text=text,
        parse_mode="HTML",
        reply_markup=CalendarUtils.main_menu()
    )

