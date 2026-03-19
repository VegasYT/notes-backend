"""init

Revision ID: b61231ce458a
Revises: 
Create Date: 2026-03-18 15:10:02.435910

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b61231ce458a'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('users',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('email', sa.String(length=255), nullable=False),
    sa.Column('hashed_password', sa.String(length=255), nullable=False),
    sa.Column('is_admin', sa.Boolean(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_users_email'), 'users', ['email'], unique=True)
    op.create_table('dashboards',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('title', sa.String(length=255), nullable=False),
    sa.Column('owner_id', sa.Integer(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['owner_id'], ['users.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_dashboards_owner_id'), 'dashboards', ['owner_id'], unique=False)
    op.create_table('dashboard_shares',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('dashboard_id', sa.Integer(), nullable=False),
    sa.Column('shared_with_user_id', sa.Integer(), nullable=False),
    sa.Column('access_level', sa.Enum('read', 'write', name='accesslevel'), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['dashboard_id'], ['dashboards.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['shared_with_user_id'], ['users.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('dashboard_id', 'shared_with_user_id', name='uq_dashboard_user')
    )
    op.create_index(op.f('ix_dashboard_shares_dashboard_id'), 'dashboard_shares', ['dashboard_id'], unique=False)
    op.create_index(op.f('ix_dashboard_shares_shared_with_user_id'), 'dashboard_shares', ['shared_with_user_id'], unique=False)
    op.create_table('notes',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('title', sa.String(length=255), nullable=False),
    sa.Column('content', sa.Text(), nullable=False),
    sa.Column('dashboard_id', sa.Integer(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['dashboard_id'], ['dashboards.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_notes_dashboard_id'), 'notes', ['dashboard_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_notes_dashboard_id'), table_name='notes')
    op.drop_table('notes')
    op.drop_index(op.f('ix_dashboard_shares_shared_with_user_id'), table_name='dashboard_shares')
    op.drop_index(op.f('ix_dashboard_shares_dashboard_id'), table_name='dashboard_shares')
    op.drop_table('dashboard_shares')
    op.drop_index(op.f('ix_dashboards_owner_id'), table_name='dashboards')
    op.drop_table('dashboards')
    op.drop_index(op.f('ix_users_email'), table_name='users')
    op.drop_table('users')
