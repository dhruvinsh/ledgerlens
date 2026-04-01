from sqlalchemy import ColumnElement, or_

from app.models.receipt import Receipt
from app.models.user import User


def receipt_visibility(user: User) -> ColumnElement[bool]:
    """Return a SQLAlchemy clause filtering receipts visible to the user.

    If the user belongs to a household with shared mode, they can see all
    household members' receipts. Otherwise, only their own.
    """
    if user.household_id:
        return or_(
            Receipt.user_id == user.id,
            Receipt.household_id == user.household_id,
        )
    return Receipt.user_id == user.id
