from google.oauth2 import service_account
from googleapiclient.discovery import build
from datetime import datetime, timedelta, timezone, time, date
from config import CALENDAR_A, CALENDAR_B
from multiprocessing import Process


SERVICE_ACCOUNT_FILE = 'credentials.json'
SCOPES = ['https://www.googleapis.com/auth/calendar']

CALENDAR_ID = {
    "A": CALENDAR_A,
    "B": CALENDAR_B
}

courts = {
    "A": 3,
    "B": 2
}

# Авторизация сервисного аккаунта
credentials = service_account.Credentials.from_service_account_file(
    SERVICE_ACCOUNT_FILE, scopes=SCOPES
)

service = build('calendar', 'v3', credentials=credentials)


def list_events():
    now = datetime.now(timezone.utc)
    time_min = now.isoformat()
    time_max = (now + timedelta(days=30)).isoformat()  # расширенный интервал для проверки

    try:
        events_result = service.events().list(
            calendarId=CALENDAR_ID,
            timeMin=time_min,
            timeMax=time_max,
            maxResults=10,
            singleEvents=True,
            orderBy='startTime',
        ).execute()
        events = events_result.get('items', [])

        if not events:
            print('В указанный период событий нет.')
        else:
            for event in events:
                start = event['start'].get('dateTime', event['start'].get('date'))
                # print(f"{start} - {event.get('summary')}")
    except Exception as e:
        print(f"Ошибка API: {e}")


WORK_START = time(6, 0)
WORK_END = time(22, 0)

# Пример списка слотов с 6:00 до 22:00 по 1 часу (можно задать любой нужный интервал)
TIME_SLOTS = [
    (time(hour, 0), time(hour+1, 0))
    for hour in range(WORK_START.hour, WORK_END.hour)
]


def check_is_it_free_slot(
    location: str,
    slot: str,
    date: datetime.date = None,
):
    if date is None:
        print("Необходимо передать дату в параметре 'date'")
        return False

    # Парсим строку слота "HH:MM-HH:MM"
    try:
        start_str, end_str = slot.split("-")
        start_hour, start_minute = map(int, start_str.split(":"))
        end_hour, end_minute = map(int, end_str.split(":"))
    except Exception as e:
        print(f"Ошибка парсинга слота: {e}")
        return False

    tz = timezone(timedelta(hours=5))  # Asia/Tashkent

    # Формируем datetime для начала и конца слота
    start_dt = datetime.combine(date, time(start_hour, start_minute), tzinfo=tz)
    end_dt = datetime.combine(date, time(end_hour, end_minute), tzinfo=tz)

    # Преобразуем в UTC для запроса к Google API
    start_utc = start_dt.astimezone(timezone.utc).isoformat()
    end_utc = end_dt.astimezone(timezone.utc).isoformat()

    try:
        events_result = service.events().list(
            calendarId=CALENDAR_ID[location],
            timeMin=start_utc,
            timeMax=end_utc,
            singleEvents=True,
            orderBy='startTime'
        ).execute()
        # print(events_result)
        events = events_result.get('items', [])
        # print(len(events))

        if len(events) >= courts[location]:
            # print(f"Слот {slot} на дату {date} занят.")
            return False  # Есть брони — слот занят
        else:
            # print(f"Слот {slot} на дату {date} свободен.")
            return True  # Нет брони — слот свободен
    except Exception as e:

        print(f"Ошибка API: {e}")
        return False

# print(check_is_it_free_slot("A", "20:00-21:00", date(2025, 10, 11)))


def returning_free_slots(location, year, month, day):

    time_slots = [
        '06:00-07:00', '07:00-08:00', '08:00-09:00',
        '09:00-10:00', '10:00-11:00', '11:00-12:00', '12:00-13:00',
        '13:00-14:00', '14:00-15:00', '15:00-16:00', '16:00-17:00',
        '17:00-18:00', '18:00-19:00', '19:00-20:00', '20:00-21:00', '21:00-22:00'
    ]

    check_date = date(year, month, day)
    lst = []
    # print(len(time_slots))
    # print()
    for slot in range(len(time_slots) - 1):
        # print("sl: ", slot)
        if not check_is_it_free_slot(location, time_slots[slot], check_date):
            lst.append(slot)

    # print(time_slots)
    # print(len(time_slots))
    for i in sorted(lst, reverse=True):
        time_slots.pop(i)

    return time_slots

# print(returning_free_slots("A", 2025, 10, 13))
def create_booking(location: str, day: str, time_slot: str, number: str, name: str):
    calendar_id = CALENDAR_ID[location]

    time_slot = time_slot.split("-")[0]
    s = f"{day}_{time_slot}"

    datetime_obj = datetime.strptime(s, "%Y-%m-%d_%H:%M").isoformat()
    # test = "2025-10-10_20:00"
    # print(datetime_obj)
    event_start = datetime.strptime(s, "%Y-%m-%d_%H:%M")

    event_end = event_start + timedelta(hours=1)

    # event_end = event_start + timedelta(hours=1)
    #
    event = {
        'summary': f'{name}',
        'description': f'{number}',
        'start': {
            'dateTime': event_start.isoformat(),
            'timeZone': 'Asia/Tashkent',
        },
        'end': {
            'dateTime': event_end.isoformat(),
            'timeZone': 'Asia/Tashkent',
        },
        'reminders': {
            'useDefault': True,
        },
    }
    created_event = service.events().insert(calendarId=calendar_id, body=event).execute()
    print(f"Событие создано: {created_event.get('htmlLink')}")


def create_booking_in_process(location: str, day: str, time_slot: str, number: str, name: str):
    """Запуск создания бронирования в отдельном процессе"""
    process = Process(
        target=create_booking,
        args=(location, day, time_slot, number, name)
    )
    process.daemon = True
    process.start()





