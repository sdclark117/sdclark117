"""Add analytics table for tracking site visits and user activity

Revision ID: add_analytics_table
Revises: 43d2ce57fcbe
Create Date: 2024-01-01 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from datetime import datetime

# revision identifiers, used by Alembic.
revision = 'add_analytics_table'
down_revision = '43d2ce57fcbe'
branch_labels = None
depends_on = None


def upgrade():
    # Create analytics table
    op.create_table('site_analytics',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('date', sa.Date(), nullable=False),
        sa.Column('total_visits', sa.Integer(), default=0),
        sa.Column('unique_visitors', sa.Integer(), default=0),
        sa.Column('registered_users', sa.Integer(), default=0),
        sa.Column('active_users', sa.Integer(), default=0),
        sa.Column('searches_performed', sa.Integer(), default=0),
        sa.Column('exports_performed', sa.Integer(), default=0),
        sa.Column('created_at', sa.DateTime(), default=datetime.utcnow),
        sa.Column('updated_at', sa.DateTime(), default=datetime.utcnow, onupdate=datetime.utcnow),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('date')
    )
    
    # Create page visits table for detailed tracking
    op.create_table('page_visits',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('date', sa.Date(), nullable=False),
        sa.Column('page', sa.String(100), nullable=False),
        sa.Column('visits', sa.Integer(), default=0),
        sa.Column('unique_visitors', sa.Integer(), default=0),
        sa.Column('created_at', sa.DateTime(), default=datetime.utcnow),
        sa.Column('updated_at', sa.DateTime(), default=datetime.utcnow, onupdate=datetime.utcnow),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('date', 'page')
    )
    
    # Create user activity table for tracking individual user actions
    op.create_table('user_activity',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('ip_address', sa.String(45), nullable=False),
        sa.Column('action', sa.String(100), nullable=False),
        sa.Column('page', sa.String(100), nullable=True),
        sa.Column('user_agent', sa.String(500), nullable=True),
        sa.Column('created_at', sa.DateTime(), default=datetime.utcnow),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes for better performance
    op.create_index('idx_site_analytics_date', 'site_analytics', ['date'])
    op.create_index('idx_page_visits_date', 'page_visits', ['date'])
    op.create_index('idx_page_visits_page', 'page_visits', ['page'])
    op.create_index('idx_user_activity_user_id', 'user_activity', ['user_id'])
    op.create_index('idx_user_activity_created_at', 'user_activity', ['created_at'])
    op.create_index('idx_user_activity_action', 'user_activity', ['action'])


def downgrade():
    # Drop indexes
    op.drop_index('idx_user_activity_action', 'user_activity')
    op.drop_index('idx_user_activity_created_at', 'user_activity')
    op.drop_index('idx_user_activity_user_id', 'user_activity')
    op.drop_index('idx_page_visits_page', 'page_visits')
    op.drop_index('idx_page_visits_date', 'page_visits')
    op.drop_index('idx_site_analytics_date', 'site_analytics')
    
    # Drop tables
    op.drop_table('user_activity')
    op.drop_table('page_visits')
    op.drop_table('site_analytics') 