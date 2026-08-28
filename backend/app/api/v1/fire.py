from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional
import math

router=APIRouter()

class FIRERequest(BaseModel):
    current_age: int
    current_savings: float
    monthly_savings: float
    monthly_expenses: float
    expected_return: float = 10
    inflation: float = 6
    target_retirement_age: Optional[int]=None
    safe_withdrawal: float = 4

@router.post("/fire/calculate")
async def fire_calc(payload: FIRERequest):
    annual_expenses = payload.monthly_expenses *12
    years_to_retire = (payload.target_retirement_age - payload.current_age) if payload.target_retirement_age else None
    corpus = annual_expenses * (100/payload.safe_withdrawal)
    if years_to_retire:
        corpus_inflated = corpus * ((1+payload.inflation/100) ** years_to_retire)
    else:
        corpus_inflated = corpus
    r = payload.expected_return/100/12
    n = years_to_retire*12 if years_to_retire else 360
    fv_current = payload.current_savings * ((1+r)**n) if r else payload.current_savings
    fv_monthly = payload.monthly_savings * (((1+r)**n -1)/r) if r else payload.monthly_savings * n
    projected = fv_current + fv_monthly
    on_track = projected >= corpus_inflated
    estimated_years=None
    if payload.monthly_savings>0:
        bal=payload.current_savings
        for m in range(1, 600):
            bal = bal*(1+r) + payload.monthly_savings
            if bal >= corpus_inflated:
                estimated_years = math.ceil(m/12)
                break
    return {
        "annual_expenses": round(annual_expenses,2),
        "required_corpus_today": round(corpus,2),
        "required_corpus_inflated": round(corpus_inflated,2),
        "projected_corpus": round(projected,2) if years_to_retire else None,
        "years_to_retirement": years_to_retire,
        "estimated_years_to_fire": estimated_years,
        "estimated_retirement_year": payload.current_age + estimated_years if estimated_years else None,
        "on_track": on_track,
        "monthly_savings": payload.monthly_savings
    }
