from pydantic import BaseModel, field_validator
from typing import Optional, Literal
from datetime import date, datetime

VALID_CATEGORIES = ["Food","Groceries","Transport","Shopping","Entertainment","Bills","Utilities","Rent","EMI","Healthcare","Education","Travel","Investment","Salary","Transfer","Other"]
PAYMENT_METHODS = ["UPI","Debit Card","Credit Card","Cash","Bank Transfer","Other","Card","Transfer"]
# legacy aliases mapping
CATEGORY_ALIASES = {"Subscriptions":"Bills", "Grocery":"Groceries"}

class TransactionCreate(BaseModel):
    date: date
    description: str
    merchant: Optional[str] = None
    amount: float
    type: Optional[str] = None  # legacy
    transaction_type: Optional[Literal["income","expense"]] = None
    category: Optional[str] = None
    subcategory: Optional[str] = None
    payment_method: Optional[str] = None
    source: Optional[Literal["manual","csv","bank_api"]] = "manual"
    account: Optional[str] = None
    notes: Optional[str] = None

    @field_validator('amount')
    @classmethod
    def amount_positive(cls, v):
        if v is not None and v <= 0:
            raise ValueError('Amount must be positive')
        return v

    @field_validator('transaction_type', mode='before')
    @classmethod
    def norm_tx_type(cls, v):
        if v: return str(v).lower().strip()
        return v

class TransactionUpdate(BaseModel):
    date: Optional[date] = None
    description: Optional[str] = None
    merchant: Optional[str] = None
    amount: Optional[float] = None
    type: Optional[str] = None
    transaction_type: Optional[Literal["income","expense"]] = None
    category: Optional[str] = None
    subcategory: Optional[str] = None
    payment_method: Optional[str] = None
    source: Optional[str] = None
    account: Optional[str] = None
    notes: Optional[str] = None

    @field_validator('amount')
    @classmethod
    def amount_positive(cls, v):
        if v is not None and v <= 0:
            raise ValueError('Amount must be positive')
        return v

class CategoryPredictRequest(BaseModel):
    description: str
    merchant: Optional[str] = None
    amount: Optional[float] = None
    payment_method: Optional[str] = None

class AnomalyRequest(BaseModel):
    amount: float
    category: Optional[str] = None
    description: Optional[str] = None

class SpendingForecastRequest(BaseModel):
    period: str = "30d"  # 7d, 30d, 90d

class BudgetRecommendRequest(BaseModel):
    income: Optional[float] = None

class GoalPredictRequest(BaseModel):
    target_amount: float
    current_amount: float
    monthly_contribution: float
    target_date: Optional[date] = None
