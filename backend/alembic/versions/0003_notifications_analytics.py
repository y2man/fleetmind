"""Phase 8: smart alerts and per-user read state for notifications.

Adds notifications.kind / link / dedupe_key (+ unique index per organization) and the
notification_reads table. The 0001 baseline builds tables from the current model metadata,
so on a brand-new database all of this already exists; every step below checks first and is a
no-op there. It upgrades databases created by Phases 4 to 7.
"""
import sqlalchemy as sa
from alembic import op

import app.models  # noqa: F401
from app.models import NotificationRead

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None

NEW_COLUMNS = [("kind", sa.String(32)), ("link", sa.String(255)), ("dedupe_key", sa.String(160))]
INDEXES = [("ix_notification_org_created", ["organization_id", "created_at"], False), ("uq_notification_dedupe", ["organization_id", "dedupe_key"], True)]


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    existing = {c["name"] for c in insp.get_columns("notifications")}
    with op.batch_alter_table("notifications") as batch:
        for name, type_ in NEW_COLUMNS:
            if name not in existing:
                batch.add_column(sa.Column(name, type_, nullable=True))
    have = {i["name"] for i in insp.get_indexes("notifications")} | {u["name"] for u in insp.get_unique_constraints("notifications")}
    for name, cols, unique in INDEXES:
        if name not in have:
            op.create_index(name, "notifications", cols, unique=unique)
    NotificationRead.__table__.create(bind=bind, checkfirst=True)


def downgrade() -> None:
    bind = op.get_bind()
    NotificationRead.__table__.drop(bind=bind, checkfirst=True)
    for name, _, _ in INDEXES:
        op.drop_index(name, table_name="notifications")
    with op.batch_alter_table("notifications") as batch:
        for name, _ in NEW_COLUMNS:
            batch.drop_column(name)
