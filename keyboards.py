from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from datetime import datetime, timedelta, date
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from google_calendar import *
from aiogram import Bot
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo

keyboard = InlineKeyboardMarkup(inline_keyboard=[
    [
        InlineKeyboardButton(text="🎾 Открыть приложение", web_app=WebAppInfo(url="https://tennisplus.uz/"))
    ]
])


res_keys = InlineKeyboardMarkup(
    inline_keyboard=
    [
        [
            InlineKeyboardButton(text="🎾 Забронировать корт", callback_data="book_court")
        ],
        [
            InlineKeyboardButton(text="📋 Мои бронирования", callback_data="my_bookings")
        ],
        [
            InlineKeyboardButton(text="ℹ️ Информация", callback_data="info"),
        ]
    ]
)


class CalendarUtils:

    @staticmethod
    def get_cancel_keyboard():
        buttons = []
        buttons.append([
            InlineKeyboardButton(
                text="🏠 Главное меню",
                callback_data="main_menu"
            )
        ])
        return InlineKeyboardMarkup(inline_keyboard=buttons)

    @staticmethod
    def get_date_keyboard(days_ahead: int = 7) -> InlineKeyboardMarkup:
        """Создает клавиатуру с датами для бронирования"""
        buttons = []
        today = date.today()

        for i in range(days_ahead + 1):
            booking_date = today + timedelta(days=i)
            date_str = booking_date.strftime('%Y-%m-%d')

            if i == 0:
                display_date = f"Сегодня ({booking_date.strftime('%d.%m')})"
            elif i == 1:
                display_date = f"Завтра ({booking_date.strftime('%d.%m')})"
            else:
                weekdays = ['Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб', 'Вс']
                weekday = weekdays[booking_date.weekday()]
                display_date = f"{booking_date.strftime('%d.%m')} ({weekday})"

            buttons.append([
                InlineKeyboardButton(
                    text=display_date,
                    callback_data=f"date_{date_str}"
                )
            ])

        # Кнопка назад в главное меню
        buttons.append([
            InlineKeyboardButton(
                text="⬅️ Назад",
                callback_data="back_to_location"
            ),
            InlineKeyboardButton(
                text="🏠 Главное меню",
                callback_data="main_menu"
            )
        ])

        return InlineKeyboardMarkup(inline_keyboard=buttons)

    @staticmethod
    def get_time_slots_keyboard() -> InlineKeyboardMarkup:
        """Создает клавиатуру с временными слотами"""
        time_slots = [
            '09:00-10:00', '10:00-11:00', '11:00-12:00', '12:00-13:00',
            '13:00-14:00', '14:00-15:00', '15:00-16:00', '16:00-17:00',
            '17:00-18:00', '18:00-19:00', '19:00-20:00', '20:00-21:00'
        ]



        buttons = []
        # По две кнопки в ряд
        for i in range(0, len(time_slots), 2):
            row = []
            for j in range(2):
                if i + j < len(time_slots):
                    slot = time_slots[i + j]
                    row.append(InlineKeyboardButton(
                        text=slot,
                        callback_data=f"time_{slot}"
                    ))
            buttons.append(row)

        # Кнопки навигации
        buttons.append([
            InlineKeyboardButton(
                text="⬅️ Назад",
                callback_data="back_to_date"
            ),
            InlineKeyboardButton(
                text="🏠 Главное меню",
                callback_data="main_menu"
            )
        ])

        return InlineKeyboardMarkup(inline_keyboard=buttons)

    @staticmethod
    def get_loc_keys():
        buttons = []

        buttons.append([
            InlineKeyboardButton(
                text="МГУ",
                callback_data=f"location_A"
            )
        ])
        buttons.append([
            InlineKeyboardButton(
                text="Аджо",
                callback_data=f"location_B"
            )
        ])

        buttons.append([
            InlineKeyboardButton(
                text="🏠 Главное меню",
                callback_data="main_menu"
            )
        ])

        return InlineKeyboardMarkup(inline_keyboard=buttons)

    # @staticmethod
    # def get_time_free_slots(location, year, month, day):
    #     time_slots = returning_free_slots(location, year, month, day)
    #
    #     buttons = []
    #     # По две кнопки в ряд
    #     for i in range(0, len(time_slots), 2):
    #         row = []
    #         for j in range(2):
    #             if i + j < len(time_slots):
    #                 slot = time_slots[i + j]
    #                 row.append(InlineKeyboardButton(
    #                     text=slot,
    #                     callback_data=f"time_{slot}"
    #                 ))
    #         buttons.append(row)
    #
    #     # Кнопки навигации
    #     buttons.append([
    #         InlineKeyboardButton(
    #             text="⬅️ Назад",
    #             callback_data="back_to_date"
    #         ),
    #         InlineKeyboardButton(
    #             text="🏠 Главное меню",
    #             callback_data="main_menu"
    #         )
    #     ])
    #
    #     return InlineKeyboardMarkup(inline_keyboard=buttons)

    @staticmethod
    async def get_time_free_slots(location, year, month, day):
        # Запускаем синхронную функцию в отдельном потоке
        time_slots = await asyncio.to_thread(
            returning_free_slots,
            location,
            year,
            month,
            day
        )

        buttons = []
        for i in range(0, len(time_slots), 2):
            row = []
            for j in range(2):
                if i + j < len(time_slots):
                    slot = time_slots[i + j]
                    row.append(InlineKeyboardButton(
                        text=slot,
                        callback_data=f"time_{slot}"
                    ))
            buttons.append(row)

        buttons.append([
            InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_date"),
            InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")
        ])

        return InlineKeyboardMarkup(inline_keyboard=buttons)


    @staticmethod
    def get_locations_keyboard(date_str: str, time_slot: str, loc_a, loc_b) \
            -> InlineKeyboardMarkup:
        """Создает клавиатуру с доступными локациями"""
        buttons = []
        buttons.append([
            InlineKeyboardButton(
                text=loc_a,
                callback_data=f"location_{loc_a}_{date_str}_{time_slot}"
            )
        ])
        buttons.append([
            InlineKeyboardButton(
                text=loc_b,
                callback_data=f"location_{loc_b}_{date_str}_{time_slot}"
            )
        ])

        # Кнопки навигации
        buttons.append([
            InlineKeyboardButton(
                text="⬅️ Назад",
                callback_data="back_to_time"
            ),
            InlineKeyboardButton(
                text="🏠 Главное меню",
                callback_data="main_menu"
            )
        ])

        return InlineKeyboardMarkup(inline_keyboard=buttons)

    @staticmethod
    def get_courts_keyboard(av_courts, location, date, time_slot):
        buttons = []

        if location == "A":
            print(av_courts)
            if len(av_courts) == 3:
                buttons.append([
                    InlineKeyboardButton(
                        text="⬅️ Назад",
                        callback_data="back_to_location"
                    ),
                    InlineKeyboardButton(
                        text="🏠 Главное меню",
                        callback_data="main_menu"
                    )
                ])
                return InlineKeyboardMarkup(inline_keyboard=buttons), 0

            for i in range(1, 4):
                if i not in av_courts:
                    buttons.append([InlineKeyboardButton(
                        text=f"Корт {i}",
                        callback_data=f"court_{i}_{location}_{date}_{time_slot}"
                    )])

        if location == "B":
            if len(av_courts) == 2:  # проверка не заняты ли все корты
                buttons.append([
                    InlineKeyboardButton(
                        text="⬅️ Назад",
                        callback_data="back_to_location"
                    ),
                    InlineKeyboardButton(
                        text="🏠 Главное меню",
                        callback_data="main_menu"
                    )
                ])
                return InlineKeyboardMarkup(inline_keyboard=buttons), 0

            for i in range(1, 3):
                if i not in av_courts:
                    buttons.append([InlineKeyboardButton(
                        text=f"Корт {i}",
                        callback_data=f"court_{i}_{location}_{date}_{time_slot}"
                    )])

        buttons.append([
            InlineKeyboardButton(
                text="⬅️ Назад",
                callback_data="back_to_location"
            ),
            InlineKeyboardButton(
                text="🏠 Главное меню",
                callback_data="main_menu"
            )
        ])

        return InlineKeyboardMarkup(inline_keyboard=buttons), 1

    @staticmethod
    def get_booking_confirmation_keyboard(booking_id) -> InlineKeyboardMarkup:
        """Клавиатура подтверждения бронирования"""
        return InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="✅ Подтвердить",
                        callback_data=f"confirm_booking_{booking_id}"
                    )
                ],
                [
                    InlineKeyboardButton(
                        text="⬅️ Изменить время",
                        callback_data="back_to_time"
                    ),
                    InlineKeyboardButton(
                                text="🏠 Главное меню",
                                callback_data="main_menu"
                            )
                ]
            ]
        )

    @staticmethod
    def admin_keyboard(booking_info):
        buttons = []
        buttons.append([
            InlineKeyboardButton(text="Подтверждаю, платеж был проведен!✅",
                                 callback_data=f"admin_confirm_{booking_info}"),
            InlineKeyboardButton(text="Платежа не было!❌", callback_data=f"admin_cancel_{booking_info}")
        ])
        return InlineKeyboardMarkup(inline_keyboard=buttons)

    @staticmethod
    def get_info():
        buttons = []
        buttons.append(
            [
                InlineKeyboardButton(text="МГУ", callback_data="MSU"),
                InlineKeyboardButton(text="Аджо", callback_data="ajou")
            ]
        )
        return InlineKeyboardMarkup(inline_keyboard=buttons)

    @staticmethod
    def info_keys():
        buttons = []
        buttons.append(
            [
                InlineKeyboardButton(
                    text="⬅️ Вернуться назад",
                    callback_data="back_to_info"
                ),
                InlineKeyboardButton(
                    text="🏠 Главное меню",
                    callback_data="main_menu"
                )
            ]
        )
        return InlineKeyboardMarkup(inline_keyboard=buttons)

    @staticmethod
    def main_menu():
        buttons = []
        buttons.append(
            [
                InlineKeyboardButton(
                    text="🏠 Главное меню",
                    callback_data="main_menu"
                )
            ]
        )
        return InlineKeyboardMarkup(inline_keyboard=buttons)


Calendar = CalendarUtils()

registration_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [
            KeyboardButton(text="Отправить номер 📱", request_contact=True)
        ]
    ],
    resize_keyboard=True,
    one_time_keyboard=True
)

rs_confirm_keys = InlineKeyboardMarkup(
    inline_keyboard=[
        [
            InlineKeyboardButton(text="Подвтертдить", callback_data="rs_confirm"),
            InlineKeyboardButton(text="Отменить", callback_data="rs_cancel")
        ]
    ]
)
