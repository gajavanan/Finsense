"""
TransactionProvider architecture for FinSense
Future bank/AA data goes through SAME pipeline:
Bank/AA -> TransactionProvider -> normalization -> categorization -> database -> budget/anomaly/forecast -> dashboard

This file defines extensible provider interface.
Do NOT pretend we have direct bank access - placeholder only requires user consent, FIP/AA integration.
"""
from abc import ABC, abstractmethod
from typing import List, Dict, Optional
from datetime import date
import uuid

class TransactionProvider(ABC):
    """
    Extensible provider interface for fetching transactions.
    Implementations must handle authenticated user isolation.
    """
    @abstractmethod
    def fetch_accounts(self, user_id: str) -> List[Dict]:
        """Return list of accounts for user - requires user consent"""
        pass

    @abstractmethod
    def fetch_transactions(self, user_id: str, from_date: Optional[date]=None, to_date: Optional[date]=None) -> List[Dict]:
        """
        Return normalized transaction dicts: {
            date, description, merchant, amount, transaction_type, category, payment_method, source, confidence_score
        }
        Must go through normalization -> categorization -> database pipeline.
        """
        pass

class ManualTransactionProvider(TransactionProvider):
    """Manual entry provider - uses DB directly via API"""
    def fetch_accounts(self, user_id: str):
        from app.core.database import SessionLocal
        from app.models import ConnectedAccount
        db = SessionLocal()
        try:
            accounts = db.query(ConnectedAccount).filter(ConnectedAccount.user_id==user_id).all()
            return [{"id": a.id, "name": a.account_name, "provider": a.provider, "balance": float(a.balance)} for a in accounts]
        finally:
            db.close()

    def fetch_transactions(self, user_id: str, from_date=None, to_date=None):
        from app.core.database import SessionLocal
        from app.models import Transaction
        db = SessionLocal()
        try:
            q = db.query(Transaction).filter(Transaction.user_id==user_id)
            if from_date: q = q.filter(Transaction.date >= from_date)
            if to_date: q = q.filter(Transaction.date <= to_date)
            txs = q.limit(200).all()
            return [
                {
                    "id": t.id,
                    "date": t.date.isoformat() if t.date else None,
                    "description": t.description,
                    "merchant": t.merchant,
                    "amount": float(t.amount),
                    "transaction_type": getattr(t, 'transaction_type', None) or getattr(t, 'type', None),
                    "category": t.category,
                    "payment_method": t.payment_method,
                    "source": getattr(t, 'source', 'manual'),
                } for t in txs
            ]
        finally:
            db.close()

class CSVTransactionProvider(TransactionProvider):
    """CSV file provider - parses uploaded statement and normalizes"""
    def __init__(self, file_path: Optional[str]=None, dataframe=None):
        self.file_path = file_path
        self.df = dataframe

    def fetch_accounts(self, user_id: str):
        return [{"id": "csv", "name": "CSV Import", "provider": "csv", "balance": 0}]

    def fetch_transactions(self, user_id: str, from_date=None, to_date=None):
        # Normalization layer already implemented in transactions.py import endpoint
        # This provider is placeholder for programmatic CSV processing
        # Real usage: call normalization logic shared with import endpoint
        raise NotImplementedError("Use POST /api/v1/transactions/import for CSV parsing with normalization layer. This provider wraps that logic for future pipeline.")

class AccountAggregatorProvider(TransactionProvider):
    """
    PLACEHOLDER ARCHITECTURE ONLY for Real Bank / Account Aggregator integration.

    Production integration requires:
    - User consent via AA consent artefact (explicit opt-in)
    - Financial Information Provider (FIP) / AA integration (e.g., Setu, Finvu, OneMoney)
    - Secure authentication (OAuth, regulated AA flow)
    - Regulatory/provider onboarding (RBI AA framework in India)
    - Data encryption in transit/at rest, audit logging

    DO NOT create fake bank transactions - this provider intentionally returns empty and documents requirements.

    Future flow:
        Bank/AA (with consent) -> AccountAggregatorProvider.fetch_transactions()
        -> normalization (Date/Amount/Type mapping) -> categorize_transaction() -> database (user_id isolated)
        -> budget check -> anomaly detection -> forecast -> dashboard -> AI recommendations
    """
    def __init__(self, consent_id: Optional[str]=None, aa_config: Optional[Dict]=None):
        self.consent_id = consent_id
        self.aa_config = aa_config or {}

    def fetch_accounts(self, user_id: str):
        # In production: call AA /accounts API with consent_id
        raise NotImplementedError(
            "AccountAggregatorProvider not configured. Requires user consent, AA integration, and provider onboarding. "
            "See https://sahamati.org.in/account-aggregator for RBI AA framework."
        )

    def fetch_transactions(self, user_id: str, from_date=None, to_date=None):
        if not self.consent_id:
            raise ValueError("User consent required for Account Aggregator data fetch. No consent_id provided.")
        # In production: fetch from FIP via AA, normalize, categorize, store
        raise NotImplementedError(
            "Real bank data fetch not implemented. Requires FIP/AA integration, secure auth, and regulatory approval. "
            "Placeholder ensures architecture is ready without faking data."
        )

# Factory helper
def get_provider(provider_type: str, **kwargs) -> TransactionProvider:
    """Factory to get provider by type: manual, csv, account_aggregator"""
    if provider_type == "manual":
        return ManualTransactionProvider()
    elif provider_type == "csv":
        return CSVTransactionProvider(**kwargs)
    elif provider_type == "account_aggregator":
        return AccountAggregatorProvider(**kwargs)
    else:
        raise ValueError(f"Unknown provider type: {provider_type}")
