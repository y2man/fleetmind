RESOURCES = ["vehicles", "drivers", "deliveries", "routes", "fuel", "maintenance"]
PERMISSIONS = (
    [f"{r}:{a}" for r in RESOURCES for a in ("read", "write")]
    + ["analytics:read", "ai:use", "users:read", "users:manage", "audit:read", "org:manage"]
)
_reads = [f"{r}:read" for r in RESOURCES] + ["analytics:read"]

ROLE_PERMISSIONS: dict[str, set[str]] = {
    "owner": set(PERMISSIONS),
    "admin": set(PERMISSIONS) - {"org:manage"},
    "dispatcher": set(_reads) | {"deliveries:write", "routes:write", "ai:use"},
    "viewer": set(_reads),
}
ASSIGNABLE_ROLES = ["admin", "dispatcher", "viewer"]


def permissions_for(role: str) -> set[str]:
    return ROLE_PERMISSIONS.get(role, set())
