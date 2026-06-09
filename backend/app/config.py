from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = "ExpenseTracker"
    debug: bool = False
    secret_key: str = "change-this-to-a-random-secret-key-min-32-chars"

    # Full SQLAlchemy URL — sqlite:///... for local dev, postgresql://... for production
    database_url: str = "sqlite:///./data/database/expense_tracker.db"

    # Fernet key for encrypting OAuth tokens and TOTP secrets.
    # Generate with: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
    encryption_key: str = ""

    google_client_id: str = ""
    google_client_secret: str = ""
    google_redirect_uri: str = "http://localhost:3000/auth/gmail/callback"

    # Comma-separated list of allowed CORS origins, e.g. "http://localhost:3000,https://yourdomain.com"
    allowed_origins: str = "http://localhost:3000"

    enable_totp: bool = False

    session_expire_hours: int = 24
    jwt_expire_minutes: int = 43200  # 30 days
    email_retention_days: int = 30

    class Config:
        env_file = ".env"

    @property
    def allowed_origins_list(self) -> list:
        return [o.strip() for o in self.allowed_origins.split(",")]


settings = Settings()
