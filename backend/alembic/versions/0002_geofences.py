"""Phase 6: geofences.

The 0001 baseline builds tables from the current model metadata, so on a brand-new
database `geofences` already exists by the time this runs. checkfirst makes this
revision a no-op there and creates the table on databases made by Phase 4/5.
Delivery and stop coordinates already exist in 0001 (pickup_lat, dest_lat, stops.lat ...).
"""
from alembic import op

import app.models  # noqa: F401
from app.models import Geofence

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    Geofence.__table__.create(bind=op.get_bind(), checkfirst=True)


def downgrade() -> None:
    Geofence.__table__.drop(bind=op.get_bind(), checkfirst=True)
