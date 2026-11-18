"""Add GPS device credentials, customer tracking links and delivery contacts."""
import sqlalchemy as sa
from alembic import op

import app.models  # noqa: F401
from app.models import CustomerTrackingLink, GPSDeviceCredential

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    existing_columns = {c["name"] for c in sa.inspect(bind).get_columns("deliveries")}
    with op.batch_alter_table("deliveries") as batch:
        for name, type_ in (
            ("customer_name", sa.String(160)),
            ("customer_phone", sa.String(40)),
            ("customer_email", sa.String(254)),
        ):
            if name not in existing_columns:
                batch.add_column(sa.Column(name, type_, nullable=True))
    GPSDeviceCredential.__table__.create(bind=bind, checkfirst=True)
    CustomerTrackingLink.__table__.create(bind=bind, checkfirst=True)


def downgrade() -> None:
    bind = op.get_bind()
    CustomerTrackingLink.__table__.drop(bind=bind, checkfirst=True)
    GPSDeviceCredential.__table__.drop(bind=bind, checkfirst=True)
    with op.batch_alter_table("deliveries") as batch:
        for name in ("customer_email", "customer_phone", "customer_name"):
            batch.drop_column(name)
