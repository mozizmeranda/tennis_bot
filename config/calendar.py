from pydantic import BaseModel
from typing import List


class CalendarBase(BaseModel):
    name: str
    max_events_per_hour: int


class CalendarResponse(CalendarBase):
    id: int

    class Config:
        from_attributes = True


class CreateCalendar(BaseModel):
    name: str
    max_events_per_hour: int


class CreateUser(BaseModel):
    telegram_id: int
    username: str
    full_name: str


class CalendarMembers(BaseModel):
    telegram_id: int
    calendar_id: int


