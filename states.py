from aiogram.fsm.state import State, StatesGroup


class RegistrationStates(StatesGroup):
    waiting_phone = State()


class Booking(StatesGroup):
    day = State()
    time = State()
    location = State()
    court = State()
    screenshot = State()

class Mailing(StatesGroup):
    get_text = State()
    confirm_mailing = State()
