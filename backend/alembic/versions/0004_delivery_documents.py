"""Add private delivery proof metadata."""
from alembic import op

import app.models  # noqa: F401
from app.models import DeliveryDocument

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    DeliveryDocument.__table__.create(bind=op.get_bind(), checkfirst=True)


def downgrade() -> None:
    DeliveryDocument.__table__.drop(bind=op.get_bind(), checkfirst=True)
