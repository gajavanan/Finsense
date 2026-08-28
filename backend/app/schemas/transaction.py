from pydantic import BaseModel
from typing import Optional
from datetime import date, datetime

class TransactionCreate(BaseModel):
    date: date
    description: str
    amount: float
    type: str  # income, expense, transfer
    category: Optional[str] = None
    payment_method: Optional[str] = None
    merchant: Optional[str] = None
    account: Optional[str] = None
    notes: Optional[str] = None

class TransactionUpdate(BaseModel):
    date: Optional[date] = None
    description: Optional[str] = None
    amount: Optional[float] = None
    type: Optional[str] = None
    category: Optional[str] = None
    payment_method: Optional[str] = None
    merchant: Optional[str] = None
    account: Optional[str] = None
    notes: Optional[str] = None

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
