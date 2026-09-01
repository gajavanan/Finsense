"""phase1_and_spending_alerts

Revision ID: 002_phase1_and_spending_alerts
Revises: 001_initial
Create Date: 2026-09-01
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = '002_phase1_and_spending_alerts'
down_revision: Union[str, None] = '001_initial'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    # 1. Create spending_alerts table
    op.create_table(
        'spending_alerts',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('user_id', sa.String(), nullable=False),
        sa.Column('alert_type', sa.String(), nullable=False),
        sa.Column('category', sa.String(), nullable=False),
        sa.Column('message', sa.Text(), nullable=False),
        sa.Column('amount', sa.Numeric(12, 2), nullable=True),
        sa.Column('is_read', sa.Boolean(), server_default=sa.text('false'), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_spending_alerts_user_id', 'spending_alerts', ['user_id'])
    op.create_index('ix_spending_alerts_category', 'spending_alerts', ['category'])

    # 2. Add columns to transactions
    op.add_column('transactions', sa.Column('transaction_type', sa.String(), nullable=True))
    op.add_column('transactions', sa.Column('subcategory', sa.String(), nullable=True))
    op.add_column('transactions', sa.Column('source', sa.String(), server_default='manual', nullable=True))
    op.add_column('transactions', sa.Column('confidence_score', sa.Numeric(5, 4), nullable=True))
    op.add_column('transactions', sa.Column('is_anomaly', sa.Boolean(), server_default=sa.text('false'), nullable=True))
    op.add_column('transactions', sa.Column('updated_at', sa.DateTime(), nullable=True))
    op.create_index('ix_transactions_category', 'transactions', ['category'])
    op.create_index('ix_transactions_transaction_type', 'transactions', ['transaction_type'])

    # 3. Add columns to budgets
    op.add_column('budgets', sa.Column('monthly_limit', sa.Numeric(12, 2), nullable=True))
    op.add_column('budgets', sa.Column('year', sa.String(), nullable=True))
    op.add_column('budgets', sa.Column('updated_at', sa.DateTime(), nullable=True))

    # 4. Add columns to users
    op.add_column('users', sa.Column('verification_token_expires', sa.DateTime(), nullable=True))

def downgrade() -> None:
    op.drop_column('users', 'verification_token_expires')
    op.drop_column('budgets', 'updated_at')
    op.drop_column('budgets', 'year')
    op.drop_column('budgets', 'monthly_limit')
    op.drop_index('ix_transactions_transaction_type', table_name='transactions')
    op.drop_index('ix_transactions_category', table_name='transactions')
    op.drop_column('transactions', 'updated_at')
    op.drop_column('transactions', 'is_anomaly')
    op.drop_column('transactions', 'confidence_score')
    op.drop_column('transactions', 'source')
    op.drop_column('transactions', 'subcategory')
    op.drop_column('transactions', 'transaction_type')
    op.drop_index('ix_spending_alerts_category', table_name='spending_alerts')
    op.drop_index('ix_spending_alerts_user_id', table_name='spending_alerts')
    op.drop_table('spending_alerts')
