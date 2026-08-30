from pydantic import BaseModel, Field
from typing import List


class CreateInvoiceRequest(BaseModel):
    temporary_booking_id: str
    telegram_id: int
    price: int = Field(gt=0, description="Цена должна быть строго больше нуля")
    location: str


class GetFullPriceBody(BaseModel):
    free_courts_quantity: int
    location: str
    day: str
    telegram_id: int
    time_slots: List[str]


class GetInvoice(BaseModel):
    order_id: str



