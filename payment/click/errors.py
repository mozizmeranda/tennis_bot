"""
Коды ошибок Click.uz — возвращаются в ответах на /prepare и /complete.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class ClickError:
    code: int
    note: str

    def as_dict(self, click_trans_id: int = 0, merchant_trans_id: str = "") -> dict:
        return {
            "click_trans_id": click_trans_id,
            "merchant_trans_id": merchant_trans_id,
            "error": self.code,
            "error_note": self.note,
        }


# Коды, которые мы возвращаем Click
SUCCESS              = ClickError(0,  "Success")
INVALID_SIGN         = ClickError(-1, "Invalid sign")
INVALID_AMOUNT       = ClickError(-2, "Invalid amount")
TRANSACTION_ERROR    = ClickError(-3, "Transaction error")
ALREADY_PAID         = ClickError(-4, "Order already paid or cancelled")
ORDER_NOT_FOUND      = ClickError(-5, "Order not found")
TRANSACTION_NOT_FOUND = ClickError(-6, "Transaction not found")
SERVER_ERROR         = ClickError(-9, "Internal server error")

# Коды, которые Click присылает нам в Complete (поле error)
CLICK_STATUS_MAP = {
    0:  "paid",
    -1: "failed",
    -4: "cancelled",
    -5: "failed",
    -6: "failed",
}