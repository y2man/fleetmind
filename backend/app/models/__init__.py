from app.models.org import AuditLog, Organization, Permission, Role, User, role_permissions  # noqa: F401
from app.models.documents import DeliveryDocument  # noqa: F401
from app.models.integrations import CustomerTrackingLink, GPSDeviceCredential  # noqa: F401
from app.models.fleet import (  # noqa: F401
    AIInsight, Delivery, Driver, FuelTransaction, Geofence, Inspection, MaintenanceRecord,
    Notification, NotificationRead, Route, Stop, Vehicle, VehicleLocation,
)
