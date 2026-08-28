import uuid
from sqlalchemy import Column, String, Numeric, Date, DateTime, Boolean, Text, ForeignKey, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base
import uuid as pyuuid
from datetime import datetime

def gen_uuid():
    return str(pyuuid.uuid4())

class User(Base):
    __tablename__ = "users"
    id = Column(String, primary_key=True, default=gen_uuid)
    email = Column(String, unique=True, nullable=False, index=True)
    hashed_password = Column(String, nullable=False)
    full_name = Column(String, nullable=True)
    is_verified = Column(Boolean, default=False)
    verification_token = Column(String, nullable=True)
    verification_token_expires = Column(DateTime, nullable=True)
    reset_token = Column(String, nullable=True)
    reset_token_expires = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class Profile(Base):
    __tablename__ = "profiles"
    id = Column(String, primary_key=True)  # same as user id
    full_name = Column(String)
    email = Column(String)
    avatar_url = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class Transaction(Base):
    __tablename__ = "transactions"
    id = Column(String, primary_key=True, default=gen_uuid)
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    date = Column(Date, nullable=False)
    description = Column(String, nullable=False)
    amount = Column(Numeric(12,2), nullable=False)
    type = Column(String, nullable=False)
    category = Column(String)
    payment_method = Column(String)
    merchant = Column(String)
    account = Column(String)
    notes = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)

class Budget(Base):
    __tablename__ = "budgets"
    id = Column(String, primary_key=True, default=gen_uuid)
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    category = Column(String, nullable=False)
    amount = Column(Numeric(12,2), nullable=False)
    period = Column(String, default="monthly")
    month = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)

class Goal(Base):
    __tablename__ = "goals"
    id = Column(String, primary_key=True, default=gen_uuid)
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String, nullable=False)
    target_amount = Column(Numeric(12,2), nullable=False)
    current_amount = Column(Numeric(12,2), default=0)
    target_date = Column(Date)
    category = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)

class Asset(Base):
    __tablename__ = "assets"
    id = Column(String, primary_key=True, default=gen_uuid)
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String, nullable=False)
    symbol = Column(String)
    type = Column(String, nullable=False)
    quantity = Column(Numeric(12,4), nullable=False)
    purchase_price = Column(Numeric(12,2), nullable=False)
    current_price = Column(Numeric(12,2))
    created_at = Column(DateTime, default=datetime.utcnow)

class Notification(Base):
    __tablename__ = "notifications"
    id = Column(String, primary_key=True, default=gen_uuid)
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    title = Column(String, nullable=False)
    message = Column(Text)
    type = Column(String, default="info")
    read = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

class AgentInsight(Base):
    __tablename__ = "agent_insights"
    id = Column(String, primary_key=True, default=gen_uuid)
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    title = Column(String, nullable=False)
    content = Column(Text)
    type = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)

class AgentAction(Base):
    __tablename__ = "agent_actions"
    id = Column(String, primary_key=True, default=gen_uuid)
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    action = Column(String, nullable=False)
    payload = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)

class ChatMessage(Base):
    __tablename__ = "chat_messages"
    id = Column(String, primary_key=True, default=gen_uuid)
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    role = Column(String, nullable=False)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

class AgentPreference(Base):
    __tablename__ = "agent_preferences"
    id = Column(String, primary_key=True, default=gen_uuid)
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), unique=True, index=True)
    preferences = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)

class UpiAccount(Base):
    __tablename__ = "upi_accounts"
    id = Column(String, primary_key=True, default=gen_uuid)
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    upi_id = Column(String, nullable=False)
    bank_name = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)

class ConnectedAccount(Base):
    __tablename__ = "connected_accounts"
    id = Column(String, primary_key=True, default=gen_uuid)
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    provider = Column(String)
    account_name = Column(String)
    balance = Column(Numeric(12,2), default=0)
    created_at = Column(DateTime, default=datetime.utcnow)

class LoginEvent(Base):
    __tablename__ = "login_events"
    id = Column(String, primary_key=True, default=gen_uuid)
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    email = Column(String)
    user_agent = Column(String)
    ip = Column(String)
    device = Column(String)
    browser = Column(String)
    os = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
