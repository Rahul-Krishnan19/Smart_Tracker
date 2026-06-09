"""
Encryption service using Fernet symmetric encryption.
Set ENCRYPTION_KEY env var to a base64 Fernet key.
Generate one with: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
"""
from cryptography.fernet import Fernet
from app.config import settings


class CryptoService:
    _instance = None
    _fernet = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def _get_fernet(self) -> Fernet:
        if self._fernet is None:
            if not settings.encryption_key:
                raise RuntimeError(
                    "ENCRYPTION_KEY is not set. "
                    "Generate one with: python -c \"from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())\""
                )
            self._fernet = Fernet(settings.encryption_key.encode())
        return self._fernet

    def encrypt(self, plaintext: str) -> str:
        """Encrypt a string and return base64-encoded ciphertext."""
        return self._get_fernet().encrypt(plaintext.encode()).decode()

    def decrypt(self, ciphertext: str) -> str:
        """Decrypt a base64-encoded ciphertext and return plaintext."""
        return self._get_fernet().decrypt(ciphertext.encode()).decode()


crypto_service = CryptoService()
