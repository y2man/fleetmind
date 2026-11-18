# Auth and data model (Phase 4)
- Passwords: scrypt. Access token: JWT, 30 min, kept in memory by the SPA. Refresh token: JWT in an httpOnly, SameSite=Lax cookie scoped to /api/v1/auth. `Secure` is on in production.
- Email verification, password reset (single-use, tied to the current password hash) and invitations use signed, expiring tokens. Configure Resend (`RESEND_API_KEY`, verified `EMAIL_FROM`) or SMTP to send them; a development link is returned only when delivery fails or no provider is configured.
- Rate limits (per IP, in memory): register 5/min, login 10/min, forgot 5/min. Move to Redis when running several API instances, and make sure the proxy forwards the real client IP.
- RBAC: `core/rbac.py` is the source of truth, mirrored into `roles` and `permissions` tables by `services/rbac.ensure_roles`.
- Tenant isolation: every tenant table has `organization_id`; repositories filter by the caller's organization, and cross-organization IDs return 404.
- Migrations: `0001_initial` creates the schema from the model metadata. For every later change run `alembic revision --autogenerate -m "..."`.
