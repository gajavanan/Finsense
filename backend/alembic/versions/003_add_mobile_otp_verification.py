"""add_mobile_otp_verification

Revision ID: 003_add_mobile_otp_verification
Revises: 002_phase1_and_spending_alerts
Create Date: 2026-09-01
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = '003_add_mobile_otp_verification'
down_revision: Union[str, None] = '002_phase1_and_spending_alerts'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    # Add mobile OTP verification columns to users
    op.add_column('users', sa.Column('phone_number', sa.String(20), nullable=True))
    op.add_column('users', sa.Column('phone_verified', sa.Boolean(), server_default=sa.text('false'), nullable=False))
    op.add_column('users', sa.Column('phone_verified_at', sa.DateTime(timezone=True), nullable=True))
    op.create_index('ix_users_phone_number', 'users', ['phone_number'], unique=True)

def downgrade() -> None:
    op.drop_index('ix_users_phone_number', table_name='users')
    op.drop_column('users', 'phone_verified_at')
    op.drop_column('users', 'phone_verified')
    op.drop_column('users', 'phone_number')
