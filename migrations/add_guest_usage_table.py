"""Add GuestUsage table for tracking guest user searches.

Revision ID: add_guest_usage_table
Revises: 43d2ce57fcbe
Create Date: 2024-01-01 12:00:00.000000

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "add_guest_usage_table"
down_revision = "43d2ce57fcbe"
branch_labels = None
depends_on = None


def upgrade():
    """Add GuestUsage table."""
    op.create_table(
        "guest_usage",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("ip_address", sa.String(length=45), nullable=False),
        sa.Column("user_agent", sa.String(length=500), nullable=True),
        sa.Column("search_count", sa.Integer(), nullable=True),
        sa.Column("first_visit", sa.DateTime(), nullable=True),
        sa.Column("last_visit", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_guest_usage_ip_address"), "guest_usage", ["ip_address"], unique=False
    )


def downgrade():
    """Remove GuestUsage table."""
    op.drop_index(op.f("ix_guest_usage_ip_address"), table_name="guest_usage")
    op.drop_table("guest_usage")
