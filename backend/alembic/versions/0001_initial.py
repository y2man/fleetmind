"""Initial schema (users, organizations, RBAC, fleet, AI, audit).

This baseline creates tables from the model metadata. Every later change should be an
explicit revision: `alembic revision --autogenerate -m "describe change"`.
"""
from alembic import op

import app.models  # noqa: F401
from app.core.database import Base

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    Base.metadata.create_all(bind=op.get_bind())


def downgrade() -> None:
    Base.metadata.drop_all(bind=op.get_bind())
