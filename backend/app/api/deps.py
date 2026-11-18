import uuid

from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.rbac import permissions_for
from app.core.security import decode_token
from app.models import User

bearer = HTTPBearer(auto_error=False)


def client_ip(request: Request) -> str | None:
    return request.client.host if request.client else None


def get_current_user(creds: HTTPAuthorizationCredentials | None = Depends(bearer), db: Session = Depends(get_db)) -> User:
    unauthorized = HTTPException(401, "Not authenticated", headers={"WWW-Authenticate": "Bearer"})
    if not creds:
        raise unauthorized
    try:
        payload = decode_token(creds.credentials, "access")
        user = db.get(User, uuid.UUID(payload["sub"]))
    except (ValueError, KeyError):
        raise unauthorized
    if not user or not user.is_active or str(user.organization_id) != payload.get("org"):
        raise unauthorized
    return user


def require(permission: str):
    def dep(user: User = Depends(get_current_user)) -> User:
        if permission not in permissions_for(user.role_name):
            raise HTTPException(403, "You don't have permission to do that")
        return user

    return dep
