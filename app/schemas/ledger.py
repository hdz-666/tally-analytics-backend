from pydantic import BaseModel
from datetime import date


class LedgerHealthSchema(BaseModel):
    customer: str
    outstanding_amount: float
    credit_days: int
    dso_estimate: float | None = None
    revenue_12m: float
    last_invoice_date: date | None = None
    last_receipt_date: date | None = None
    days_since_last_receipt: int
    has_overdue: bool
    total_invoices: int
    total_receipts: int
    total_invoiced: float
    total_received: float
    overdue_days: int
    aging_bucket: str
    score_dso: float
    score_aging: float
    score_recency: float
    score_engagement: float
    score_balance_ratio: float
    health_score: float
    health_rag: str


class AgingSummarySchema(BaseModel):
    total_receivable: float
    current_ar: float
    overdue_1_30: float
    overdue_31_60: float
    overdue_60plus: float
    credit_balance: float
    current_count: int
    overdue_1_30_count: int
    overdue_31_60_count: int
    overdue_60plus_count: int
    credit_count: int
    total_revenue_12m: float
    portfolio_dso: float | None = None
    best_possible_dso: float | None = None
    add_days: float | None = None


class PnlMonthlySchema(BaseModel):
    month: date
    revenue: float
    cogs: float
    gross_profit: float
    gross_margin_pct: float | None = None
    fixed_costs: float
    loan_interest: float
    total_overhead: float
    net_profit: float
    net_margin_pct: float | None = None
