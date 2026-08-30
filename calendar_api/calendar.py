# routers/calendars.py
import logging
from datetime import date, datetime, time, timedelta
from typing import List, Optional

from fastapi import APIRouter, Header, HTTPException, Query

from database.database import db

from config.calendar import CalendarResponse, CreateCalendar, CreateUser, CalendarMembers
from config.event import (
    GridEventResponse,
    RecurringEventCreate,
    RecurringEventResponse,
    SingleEventCreate,
    SingleEventResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1/calendars", tags=["Calendars"])


# ─── helpers ─────────────────────────────────────────────────────────────────

def get_telegram_id(x_telegram_id: int = Header(..., alias="X-Telegram-Id")) -> int:
    if not x_telegram_id:
        raise HTTPException(status_code=401, detail="Header X-Telegram-Id is required")
    return x_telegram_id


async def require_calendar_access(calendar_id: int, telegram_id: int) -> dict:
    """Проверяет доступ и возвращает данные календаря. 403 если нет доступа."""
    has_access = await db.check_member_access(calendar_id, telegram_id)
    if not has_access:
        raise HTTPException(status_code=403, detail="You do not have access to this calendar")
    calendar = await db.get_calendar(calendar_id)
    if not calendar:
        raise HTTPException(status_code=404, detail="Calendar not found")
    return calendar


def _build_grid(
    single_rows: List[dict],
    cancelled_ids: set,
    recurring_rows: List[dict],
    from_date: date,
    to_date: date,
) -> List[dict]:
    """Собирает сетку событий из одиночных + виртуальных повторяющихся."""
    grid = []

    for e in single_rows:
        grid.append({
            "id": e["id"],
            "type": "single",
            "title": e["title"],
            "start_datetime": e["start_datetime"],
            "end_datetime": e["end_datetime"],
            "status": e["status"],
            "recurring_event_id": e["recurring_event_id"],
        })

    current = from_date
    while current <= to_date:
        weekday = current.weekday()
        for re in recurring_rows:
            if re["day_of_week"] == weekday and re["id"] not in cancelled_ids:
                grid.append({
                    "id": re["id"],
                    "type": "recurring_instance",
                    "title": re["title"],
                    "start_datetime": f"{current} {re['start_time']}",
                    "end_datetime": f"{current} {re['end_time']}",
                    "status": "confirmed",
                    "recurring_event_id": re["id"],
                })
        current += timedelta(days=1)

    grid.sort(key=lambda e: e["start_datetime"])
    return grid


async def _check_capacity(
    calendar_id: int,
    start_dt: str,
    end_dt: str,
    max_events: int,
    exclude_event_id: Optional[int] = None,
):
    """Проверяет, не превышен ли лимит событий в час. Бросает 400 если превышен."""
    start = datetime.fromisoformat(start_dt)
    end = datetime.fromisoformat(end_dt)
    from_date = start.date()
    to_date = end.date()

    from_str = f"{from_date} 00:00:00"
    to_str = f"{to_date} 23:59:59"

    active = await db.get_single_events_for_calendar(
        calendar_id, from_str, to_str, statuses=["confirmed", "pending_payment"]
    )
    cancelled = await db.get_single_events_for_calendar(
        calendar_id, from_str, to_str, statuses=["cancelled"]
    )
    cancelled_ids = {
        e["recurring_event_id"] for e in cancelled if e["recurring_event_id"] is not None
    }
    recurring = await db.get_recurring_events_for_calendar(calendar_id)

    # строим виртуальную сетку
    grid = _build_grid(active, cancelled_ids, recurring, from_date, to_date)

    # исключаем редактируемое событие
    if exclude_event_id is not None:
        grid = [e for e in grid if not (e["type"] == "single" and e["id"] == exclude_event_id)]

    # проверяем почасовые блоки
    current_hour = start.replace(minute=0, second=0, microsecond=0)
    end_hour = end.replace(minute=0, second=0, microsecond=0)
    if end.minute > 0 or end.second > 0:
        end_hour += timedelta(hours=1)

    while current_hour < end_hour:
        block_end = current_hour + timedelta(hours=1)
        count = sum(
            1 for e in grid
            if datetime.fromisoformat(e["start_datetime"]) < block_end
            and datetime.fromisoformat(e["end_datetime"]) > current_hour
        )
        if count + 1 > max_events:
            raise HTTPException(
                status_code=400,
                detail=f"Limit reached: max {max_events} events/hour at {current_hour.time().isoformat()}"
            )
        current_hour += timedelta(hours=1)


# ─── endpoints ────────────────────────────────────────────────────────────────

@router.get("", response_model=List[CalendarResponse])
async def list_calendars(telegram_id: int = Header(..., alias="X-Telegram-Id")):
    """Список всех календарей пользователя."""
    return await db.get_user_calendars(telegram_id)


@router.get("/{calendar_id}/events")
async def get_events(
    calendar_id: int,
    from_date: date = Query(...),
    to_date: date = Query(...),
    telegram_id: int = Header(..., alias="X-Telegram-Id"),
):
    """Сетка событий (одиночные + виртуальные повторяющиеся) за период."""
    await require_calendar_access(calendar_id, telegram_id)

    from_str = f"{from_date} 00:00:00"
    to_str = f"{to_date} 23:59:59"

    active = await db.get_single_events_for_calendar(
        calendar_id, from_str, to_str, statuses=["confirmed", "pending_payment"]
    )
    cancelled = await db.get_single_events_for_calendar(
        calendar_id, from_str, to_str, statuses=["cancelled"]
    )
    cancelled_ids = {
        e["recurring_event_id"] for e in cancelled if e["recurring_event_id"] is not None
    }
    recurring = await db.get_recurring_events_for_calendar(calendar_id)

    return _build_grid(active, cancelled_ids, recurring, from_date, to_date)


@router.post("/{calendar_id}/single-events", status_code=201)
async def create_single_event(
    calendar_id: int,
    event_in: SingleEventCreate,
    telegram_id: int = Header(..., alias="X-Telegram-Id"),
):
    """Создать одиночное событие."""
    calendar = await require_calendar_access(calendar_id, telegram_id)

    start_str = event_in.start_datetime.strftime("%Y-%m-%d %H:%M:%S")
    end_str = event_in.end_datetime.strftime("%Y-%m-%d %H:%M:%S")

    await _check_capacity(calendar_id, start_str, end_str, calendar["max_events_per_hour"])

    event = await db.create_single_event(
        calendar_id=calendar_id,
        created_by=telegram_id,
        title=event_in.title,
        start_datetime=start_str,
        end_datetime=end_str,
        status=event_in.status,
    )
    if not event:
        raise HTTPException(status_code=500, detail="Failed to create event")
    return event


@router.post("/{calendar_id}/recurring-events", status_code=201)
async def create_recurring_event(
    calendar_id: int,
    event_in: RecurringEventCreate,
    telegram_id: int = Header(..., alias="X-Telegram-Id"),
):
    """Создать повторяющееся событие (для одного или нескольких дней недели)."""
    calendar = await require_calendar_access(calendar_id, telegram_id)

    start_str = event_in.start_time.strftime("%H:%M:%S")
    end_str = event_in.end_time.strftime("%H:%M:%S")

    # Проверяем лимит для каждого дня недели
    existing = await db.get_recurring_events_for_calendar(
        calendar_id, days_of_week=event_in.days_of_week
    )
    for day in event_in.days_of_week:
        events_on_day = [e for e in existing if e["day_of_week"] == day]
        count = sum(
            1 for e in events_on_day
            if e["start_time"] < end_str and e["end_time"] > start_str
        )
        if count + 1 > calendar["max_events_per_hour"]:
            raise HTTPException(
                status_code=400,
                detail=f"Limit reached for day_of_week={day} at {start_str}"
            )

    events = await db.create_recurring_events_bulk(
        calendar_id=calendar_id,
        created_by=telegram_id,
        title=event_in.title,
        days_of_week=event_in.days_of_week,
        start_time=start_str,
        end_time=end_str,
    )
    return events


@router.post("")
async def create_calendar(calendar: CreateCalendar, telegram_id: int = Header(..., alias="X-Telegram-Id")):
    clndr = await db.create_calendar(name=calendar.name, max_events_per_hour=calendar.max_events_per_hour,
                                     owner_telegram_id=telegram_id)
    return clndr


@router.post("/create_user")
async def create_calendar_user(user: CreateUser):
    created_user = await db.create_calendar_user(user.telegram_id, user.username, user.full_name)
    return created_user


@router.post("/calendar_members")
async def create_calendar_user(user: CalendarMembers):
    resp = await db.add_member(user.calendar_id, user.telegram_id)
    return resp

