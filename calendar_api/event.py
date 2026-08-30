# routers/events.py
import logging
from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Header, HTTPException

from database.database import db
from config.event import CancelInstanceRequest, SingleEventUpdate

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1", tags=["Events"])


# ─── helpers ─────────────────────────────────────────────────────────────────

async def require_calendar_access(calendar_id: int, telegram_id: int) -> dict:
    """Проверяет доступ и возвращает данные календаря. 403 если нет доступа."""
    has_access = await db.check_member_access(calendar_id, telegram_id)
    if not has_access:
        raise HTTPException(status_code=403, detail="You do not have access to this calendar")
    calendar = await db.get_calendar(calendar_id)
    if not calendar:
        raise HTTPException(status_code=404, detail="Calendar not found")
    return calendar


async def _check_capacity(
    calendar_id: int,
    start_dt: str,
    end_dt: str,
    max_events: int,
    exclude_event_id: Optional[int] = None,
):
    """Проверяет лимит событий в час. Бросает 400 если превышен."""
    from datetime import date, timedelta

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

    # Строим плоскую сетку событий
    grid = []
    for e in active:
        grid.append({"type": "single", "id": e["id"], "start": e["start_datetime"], "end": e["end_datetime"]})

    current = from_date
    while current <= to_date:
        weekday = current.weekday()
        for re in recurring:
            if re["day_of_week"] == weekday and re["id"] not in cancelled_ids:
                grid.append({
                    "type": "recurring_instance",
                    "id": re["id"],
                    "start": f"{current} {re['start_time']}",
                    "end": f"{current} {re['end_time']}",
                })
        current += timedelta(days=1)

    if exclude_event_id is not None:
        grid = [e for e in grid if not (e["type"] == "single" and e["id"] == exclude_event_id)]

    current_hour = start.replace(minute=0, second=0, microsecond=0)
    end_hour = end.replace(minute=0, second=0, microsecond=0)
    if end.minute > 0 or end.second > 0:
        end_hour += timedelta(hours=1)

    while current_hour < end_hour:
        block_end = current_hour + timedelta(hours=1)
        count = sum(
            1 for e in grid
            if datetime.fromisoformat(e["start"]) < block_end
            and datetime.fromisoformat(e["end"]) > current_hour
        )
        if count + 1 > max_events:
            raise HTTPException(
                status_code=400,
                detail=f"Limit reached: max {max_events} events/hour at {current_hour.time().isoformat()}"
            )
        current_hour += timedelta(hours=1)


# ─── endpoints ────────────────────────────────────────────────────────────────

@router.delete("/single-events/{id}")
async def delete_single_event(
    id: int,
    telegram_id: int = Header(..., alias="X-Telegram-Id"),
):
    """Удалить одиночное событие."""
    event = await db.get_single_event(id)
    if not event:
        raise HTTPException(status_code=404, detail="Single event not found")

    deleted = await db.delete_single_event(id)
    if not deleted:
        raise HTTPException(status_code=500, detail="Failed to delete event")

    return {"message": "Single event successfully deleted", "id": id}


@router.patch("/single-events/{id}")
async def update_single_event(
    id: int,
    event_update: SingleEventUpdate,
    telegram_id: int = Header(..., alias="X-Telegram-Id"),
):
    """Обновить время одиночного события."""
    event = await db.get_single_event(id)
    if not event:
        raise HTTPException(status_code=404, detail="Single event not found")

    calendar = await require_calendar_access(event["calendar_id"], telegram_id)

    start_str = event_update.start_datetime.strftime("%Y-%m-%d %H:%M:%S")
    end_str = event_update.end_datetime.strftime("%Y-%m-%d %H:%M:%S")

    await _check_capacity(
        event["calendar_id"], start_str, end_str,
        calendar["max_events_per_hour"], exclude_event_id=id
    )

    updated = await db.update_single_event(id, start_str, end_str, event_update.title)
    if not updated:
        raise HTTPException(status_code=500, detail="Failed to update event")

    return updated


@router.delete("/recurring-events/{id}")
async def delete_recurring_event(
    id: int,
    telegram_id: int = Header(..., alias="X-Telegram-Id"),
):
    """Удалить повторяющееся событие (и все его связанные экземпляры)."""
    event = await db.get_recurring_event(id)
    if not event:
        raise HTTPException(status_code=404, detail="Recurring event not found")

    deleted = await db.delete_recurring_event(id)
    if not deleted:
        raise HTTPException(status_code=500, detail="Failed to delete recurring event")

    return {"message": "Recurring event series successfully deleted", "id": id}


@router.post("/recurring-events/{id}/cancel-instance")
async def cancel_recurring_instance(
    id: int,
    request: CancelInstanceRequest,
    telegram_id: int = Header(..., alias="X-Telegram-Id"),
):
    """Отменить конкретный экземпляр повторяющегося события."""
    rec_event = await db.get_recurring_event(id)
    if not rec_event:
        raise HTTPException(status_code=404, detail="Recurring event not found")

    cancel_date_str = request.date.strftime("%Y-%m-%d")

    result = await db.cancel_recurring_instance(
        recurring_event_id=id,
        cancel_date=cancel_date_str,
        created_by=telegram_id,
    )
    if result is None:
        raise HTTPException(
            status_code=400,
            detail=f"Date {request.date} does not match the recurring event's day of the week"
        )

    return {
        "message": f"Event instance successfully cancelled for {request.date}",
        "recurring_event_id": id,
        "cancelled_date": request.date.isoformat(),
    }
