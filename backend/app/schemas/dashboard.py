from pydantic import BaseModel


class DashboardSummary(BaseModel):
    total_receipts: int
    total_spent: int  # cents
    total_items: int
    total_stores: int
    avg_receipt_total: int  # cents


class SpendingByStore(BaseModel):
    store_id: str
    store_name: str
    total: int  # cents
    receipt_count: int


class SpendingByMonth(BaseModel):
    month: str  # YYYY-MM
    total: int  # cents
    receipt_count: int


class SpendingByCategory(BaseModel):
    category: str
    total: int  # cents
    item_count: int
