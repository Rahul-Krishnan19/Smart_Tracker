"""
Authentication API routes: register, login (step 1 + TOTP step 2), logout, TOTP setup.
TOTP endpoints are disabled when ENABLE_TOTP=false (default).
"""
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.schemas.auth import (
    UserRegister, UserLogin, TOTPVerify, TOTPSetupResponse,
    LoginResponse, AuthResponse, UserOut,
)
from app.services.auth_service import auth_service
from app.models.user import User

router = APIRouter()
bearer = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer),
    db: Session = Depends(get_db),
) -> User:
    if not credentials:
        raise HTTPException(status_code=401, detail="Not authenticated")
    payload = auth_service.verify_access_token(credentials.credentials)
    user = auth_service.get_user_by_id(db, int(payload["sub"]))
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="User not found or inactive")
    return user


@router.post("/register", response_model=UserOut, status_code=201)
def register(data: UserRegister, db: Session = Depends(get_db)):
    user = auth_service.register_user(db, data.username, data.email, data.password)
    return user


@router.post("/login", response_model=LoginResponse)
def login(data: UserLogin, db: Session = Depends(get_db)):
    user = auth_service.authenticate_password(db, data.username, data.password)

    if not settings.enable_totp:
        access_token = auth_service.create_access_token(user.id, user.username)
        return LoginResponse(
            requires_totp=False,
            access_token=access_token,
            user_id=user.id,
            username=user.username,
            message="Login successful.",
        )

    temp_token = auth_service.create_temp_token(user.id)
    return LoginResponse(
        requires_totp=True,
        totp_enrolled=user.totp_enrolled,
        temp_token=temp_token,
        message="Password verified. Please complete 2FA.",
    )


@router.post("/totp/setup", response_model=TOTPSetupResponse)
def totp_setup(temp_token: str, db: Session = Depends(get_db)):
    """Generate a new TOTP secret for first-time enrollment."""
    if not settings.enable_totp:
        raise HTTPException(status_code=403, detail="TOTP is disabled on this server")
    user_id = auth_service.verify_temp_token(temp_token)
    user = auth_service.get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    secret, qr = auth_service.setup_totp(db, user)
    return TOTPSetupResponse(
        qr_code_url=qr,
        secret=secret,
        temp_token=temp_token,
    )


@router.post("/totp/verify", response_model=AuthResponse)
def totp_verify(data: TOTPVerify, request: Request, db: Session = Depends(get_db)):
    """Step 2: Verify TOTP code. Returns access token on success."""
    if not settings.enable_totp:
        raise HTTPException(status_code=403, detail="TOTP is disabled on this server")
    user_id = auth_service.verify_temp_token(data.temp_token)
    user = auth_service.get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # If not enrolled yet, this call completes enrollment
    if not user.totp_enrolled:
        if not auth_service.confirm_totp_enrollment(db, user, data.totp_code):
            raise HTTPException(status_code=400, detail="Invalid TOTP code. Please try again.")
    else:
        if not auth_service.verify_totp(user, data.totp_code):
            raise HTTPException(status_code=401, detail="Invalid TOTP code")

    access_token = auth_service.create_access_token(user.id, user.username)
    return AuthResponse(
        access_token=access_token,
        user_id=user.id,
        username=user.username,
    )


@router.post("/logout")
def logout(
    credentials: HTTPAuthorizationCredentials = Depends(bearer),
    db: Session = Depends(get_db),
):
    return {"message": "Logged out successfully"}


@router.get("/me", response_model=UserOut)
def get_me(current_user: User = Depends(get_current_user)):
    return current_user
