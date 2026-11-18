from fastapi import APIRouter, Cookie, Depends, Request, Response
from sqlalchemy.orm import Session

from app.api.deps import client_ip, get_current_user
from app.core.config import get_settings
from app.core.database import get_db
from app.core.rate_limit import rate_limit
from app.models import User
from app.schemas.auth import (ForgotIn, LoginIn, MessageOut, ProfileUpdate, RegisterIn, ResetIn, TokenIn, TokenOut, UserOut, to_user_out)
from app.services import audit, auth_service

router = APIRouter(prefix="/auth", tags=["auth"])
COOKIE = "fm_refresh"


def _set_cookie(response: Response, user: User) -> None:
    s = get_settings()
    response.set_cookie(COOKIE, auth_service.refresh_token(user), max_age=s.refresh_token_days * 86400, httponly=True,
                        samesite="lax", secure=s.cookie_secure, path="/api/v1/auth")


def _token_out(user: User, dev_link: str | None = None) -> TokenOut:
    return TokenOut(access_token=auth_service.access_token(user), user=to_user_out(user), dev_link=dev_link)


@router.post("/register", status_code=201, response_model=TokenOut, dependencies=[Depends(rate_limit("register", 5, 60))])
def register(data: RegisterIn, request: Request, response: Response, db: Session = Depends(get_db)):
    user, link = auth_service.register(db, data, client_ip(request))
    _set_cookie(response, user)
    return _token_out(user, link)


@router.post("/login", response_model=TokenOut, dependencies=[Depends(rate_limit("login", 10, 60))])
def login(data: LoginIn, request: Request, response: Response, db: Session = Depends(get_db)):
    user = auth_service.login(db, data.email, data.password, client_ip(request))
    _set_cookie(response, user)
    return _token_out(user)


@router.post("/refresh", response_model=TokenOut, dependencies=[Depends(rate_limit("refresh", 30, 60))])
def refresh(db: Session = Depends(get_db), fm_refresh: str | None = Cookie(default=None)):
    from fastapi import HTTPException
    if not fm_refresh:
        raise HTTPException(401, "Not authenticated")
    return _token_out(auth_service.user_from_refresh(db, fm_refresh))


@router.post("/logout", status_code=204)
def logout(response: Response):
    response.delete_cookie(COOKIE, path="/api/v1/auth")


@router.post("/verify-email", response_model=MessageOut, dependencies=[Depends(rate_limit("verify", 10, 60))])
def verify_email(data: TokenIn, db: Session = Depends(get_db)):
    auth_service.verify_email(db, data.token)
    return MessageOut(message="Email verified")


@router.post("/resend-verification", response_model=MessageOut, dependencies=[Depends(rate_limit("resend", 3, 60))])
def resend(user: User = Depends(get_current_user)):
    return MessageOut(message="Verification email sent", dev_link=auth_service.send_verification(user))


@router.post("/forgot-password", response_model=MessageOut, dependencies=[Depends(rate_limit("forgot", 5, 60))])
def forgot(data: ForgotIn, request: Request, db: Session = Depends(get_db)):
    link = auth_service.forgot_password(db, data.email, client_ip(request))
    return MessageOut(message="If that email has an account, a reset link has been sent", dev_link=link)


@router.post("/reset-password", response_model=MessageOut, dependencies=[Depends(rate_limit("reset", 10, 60))])
def reset(data: ResetIn, request: Request, db: Session = Depends(get_db)):
    auth_service.reset_password(db, data.token, data.new_password, client_ip(request))
    return MessageOut(message="Password updated. You can sign in now")


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)):
    return to_user_out(user)


@router.patch("/me", response_model=UserOut)
def update_me(data: ProfileUpdate, request: Request, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    for k, v in data.model_dump(exclude_unset=True).items():
        setattr(user, k, v)
    audit.record(db, "user.profile_updated", user=user, ip=client_ip(request), entity_type="user", entity_id=str(user.id))
    db.commit()
    return to_user_out(user)
