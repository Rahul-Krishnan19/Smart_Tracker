from __future__ import annotations
"""
Authentication service handling user registration, login, session management, and JWT.
"""
import secrets
import hashlib
from datetime import datetime, timedelta, timezone
from typing import Optional

import bcrypt
from jose import JWTError, jwt
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.config import settings
from app.models.user import User
from app.models.session import UserSession
from app.services.crypto_service import crypto_service
from app.services.totp_service import totp_service

ALGORITHM = "HS256"
TEMP_TOKEN_PREFIX = "temp:"


class AuthService:

    # --- Password ---

    def hash_password(self, password: str) -> str:
        return bcrypt.hashpw(password.encode(), bcrypt.gensalt(rounds=12)).decode()

    def verify_password(self, plain: str, hashed: str) -> bool:
        return bcrypt.checkpw(plain.encode(), hashed.encode())

    # --- JWT ---

    def create_access_token(self, user_id: int, username: str) -> str:
        expire = datetime.now(timezone.utc) + timedelta(minutes=settings.jwt_expire_minutes)
        payload = {
            "sub": str(user_id),
            "username": username,
            "exp": expire,
            "type": "access",
        }
        return jwt.encode(payload, settings.secret_key, algorithm=ALGORITHM)

    def create_temp_token(self, user_id: int) -> str:
        """Short-lived token issued after password verify, before TOTP verify."""
        expire = datetime.now(timezone.utc) + timedelta(minutes=5)
        payload = {
            "sub": str(user_id),
            "exp": expire,
            "type": "temp",
        }
        return jwt.encode(payload, settings.secret_key, algorithm=ALGORITHM)

    def verify_temp_token(self, token: str) -> int:
        """Returns user_id if valid temp token."""
        try:
            payload = jwt.decode(token, settings.secret_key, algorithms=[ALGORITHM])
            if payload.get("type") != "temp":
                raise HTTPException(status_code=401, detail="Invalid token type")
            return int(payload["sub"])
        except JWTError:
            raise HTTPException(status_code=401, detail="Invalid or expired token")

    def verify_access_token(self, token: str) -> dict:
        """Returns payload if valid access token."""
        try:
            payload = jwt.decode(token, settings.secret_key, algorithms=[ALGORITHM])
            if payload.get("type") != "access":
                raise HTTPException(status_code=401, detail="Invalid token type")
            return payload
        except JWTError:
            raise HTTPException(status_code=401, detail="Invalid or expired token")

    # --- Session ---

    def create_session(self, db: Session, user_id: int, ip: Optional[str] = None, ua: Optional[str] = None) -> str:
        token = secrets.token_hex(32)
        expires_at = datetime.now(timezone.utc) + timedelta(hours=settings.session_expire_hours)
        session = UserSession(
            user_id=user_id,
            session_token=token,
            expires_at=expires_at,
            ip_address=ip,
            user_agent=ua,
        )
        db.add(session)
        db.commit()
        return token

    def get_valid_session(self, db: Session, token: str) -> Optional[UserSession]:
        session = db.query(UserSession).filter(UserSession.session_token == token).first()
        if not session:
            return None
        if session.expires_at.replace(tzinfo=timezone.utc) < datetime.now(timezone.utc):
            db.delete(session)
            db.commit()
            return None
        return session

    def revoke_session(self, db: Session, token: str) -> None:
        session = db.query(UserSession).filter(UserSession.session_token == token).first()
        if session:
            db.delete(session)
            db.commit()

    def cleanup_expired_sessions(self, db: Session) -> int:
        now = datetime.now(timezone.utc)
        deleted = db.query(UserSession).filter(UserSession.expires_at < now).delete()
        db.commit()
        return deleted

    # --- User management ---

    def get_user_by_username(self, db: Session, username: str) -> Optional[User]:
        return db.query(User).filter(User.username == username).first()

    def get_user_by_id(self, db: Session, user_id: int) -> Optional[User]:
        return db.query(User).filter(User.id == user_id).first()

    def register_user(self, db: Session, username: str, email: str, password: str) -> User:
        if self.get_user_by_username(db, username):
            raise HTTPException(status_code=400, detail="Username already taken")
        if db.query(User).filter(User.email == email).first():
            raise HTTPException(status_code=400, detail="Email already registered")

        user = User(
            username=username,
            email=email,
            password_hash=self.hash_password(password),
            totp_enrolled=False,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        return user

    def authenticate_password(self, db: Session, username: str, password: str) -> User:
        user = self.get_user_by_username(db, username)
        if not user or not self.verify_password(password, user.password_hash):
            raise HTTPException(status_code=401, detail="Invalid credentials")
        if not user.is_active:
            raise HTTPException(status_code=403, detail="Account disabled")
        return user

    # --- TOTP enrollment ---

    def setup_totp(self, db: Session, user: User) -> tuple[str, str]:
        """Generate a new TOTP secret for enrollment. Returns (secret, qr_data_uri)."""
        secret = totp_service.generate_secret()
        encrypted = crypto_service.encrypt(secret)
        user.totp_secret_encrypted = encrypted
        db.commit()
        qr = totp_service.generate_qr_code_base64(secret, user.username)
        return secret, qr

    def confirm_totp_enrollment(self, db: Session, user: User, code: str) -> bool:
        """Verify TOTP code and mark enrollment as complete."""
        if not user.totp_secret_encrypted:
            return False
        secret = crypto_service.decrypt(user.totp_secret_encrypted)
        if totp_service.verify(secret, code):
            user.totp_enrolled = True
            db.commit()
            return True
        return False

    def verify_totp(self, user: User, code: str) -> bool:
        """Verify TOTP code for login."""
        if not user.totp_secret_encrypted:
            return False
        secret = crypto_service.decrypt(user.totp_secret_encrypted)
        return totp_service.verify(secret, code)


auth_service = AuthService()
