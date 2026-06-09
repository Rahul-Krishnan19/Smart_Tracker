"""
TOTP (Time-based One-Time Password) service for 2FA.
Uses pyotp for TOTP generation/verification and qrcode for QR code generation.
"""
import pyotp
import qrcode
import qrcode.image.svg
import io
import base64
from app.config import settings


class TOTPService:
    ISSUER = "ExpenseTracker"
    VALID_WINDOW = 1  # Allow 1 period (30s) either side for clock skew

    def generate_secret(self) -> str:
        """Generate a new random TOTP secret."""
        return pyotp.random_base32()

    def get_totp(self, secret: str) -> pyotp.TOTP:
        return pyotp.TOTP(secret)

    def verify(self, secret: str, code: str) -> bool:
        """Verify a TOTP code. Returns True if valid."""
        totp = self.get_totp(secret)
        return totp.verify(code, valid_window=self.VALID_WINDOW)

    def get_provisioning_uri(self, secret: str, username: str) -> str:
        """Get the otpauth:// URI for QR code generation."""
        totp = self.get_totp(secret)
        return totp.provisioning_uri(name=username, issuer_name=self.ISSUER)

    def generate_qr_code_base64(self, secret: str, username: str) -> str:
        """Generate a QR code PNG as a base64 data URI."""
        uri = self.get_provisioning_uri(secret, username)
        qr = qrcode.QRCode(version=1, box_size=10, border=4)
        qr.add_data(uri)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")

        buffer = io.BytesIO()
        img.save(buffer, format="PNG")
        buffer.seek(0)
        encoded = base64.b64encode(buffer.read()).decode()
        return f"data:image/png;base64,{encoded}"


totp_service = TOTPService()
