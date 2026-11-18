import uuid

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.api.deps import client_ip, require
from app.core.database import get_db
from app.core.rbac import ASSIGNABLE_ROLES
from app.models import User
from app.repositories import user_repo
from app.schemas.auth import AuditOut, InviteIn, MemberOut, MemberUpdate, MessageOut, OrgOut, OrgUpdate
from app.services import audit, auth_service

router = APIRouter(tags=["organization"])


@router.patch("/organization", response_model=OrgOut)
def update_org(data: OrgUpdate, request: Request, user: User = Depends(require("org:manage")), db: Session = Depends(get_db)):
    org = user.organization
    for k, v in data.model_dump(exclude_unset=True).items():
        setattr(org, k, v)
    audit.record(db, "organization.updated", user=user, ip=client_ip(request), entity_type="organization", entity_id=str(org.id))
    db.commit()
    return org


@router.get("/users", response_model=list[MemberOut])
def list_users(user: User = Depends(require("users:read")), db: Session = Depends(get_db)):
    return user_repo.list_by_org(db, user.organization_id)


@router.post("/users/invite", response_model=MessageOut, status_code=201)
def invite(data: InviteIn, request: Request, user: User = Depends(require("users:manage")), db: Session = Depends(get_db)):
    _, link = auth_service.invite(db, user, data, client_ip(request))
    return MessageOut(message=f"Invitation sent to {data.email}", dev_link=link)


@router.patch("/users/{user_id}", response_model=MemberOut)
def update_member(user_id: uuid.UUID, data: MemberUpdate, request: Request, actor: User = Depends(require("users:manage")), db: Session = Depends(get_db)):
    target = user_repo.get_in_org(db, actor.organization_id, user_id)  # other orgs look like 404
    if not target:
        raise HTTPException(404, "User not found")
    if target.id == actor.id:
        raise HTTPException(400, "You can't change your own role or status")
    if target.role_name == "owner" or (target.role_name == "admin" and actor.role_name != "owner"):
        raise HTTPException(403, "You can't modify this user")
    if data.role is not None:
        if data.role not in ASSIGNABLE_ROLES:
            raise HTTPException(422, "Invalid role")
        if data.role == "admin" and actor.role_name != "owner":
            raise HTTPException(403, "Only the owner can assign admins")
        target.role_name = data.role
    if data.is_active is not None:
        target.is_active = data.is_active
    audit.record(db, "user.updated", user=actor, ip=client_ip(request), entity_type="user", entity_id=str(target.id), detail=data.model_dump(exclude_none=True))
    db.commit()
    return target


@router.get("/audit-logs", response_model=list[AuditOut])
def audit_logs(limit: int = 20, offset: int = 0, user: User = Depends(require("audit:read")), db: Session = Depends(get_db)):
    return user_repo.audit_page(db, user.organization_id, min(max(limit, 1), 100), max(offset, 0))
