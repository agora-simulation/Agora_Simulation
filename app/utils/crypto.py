"""
Symmetrische Verschlüsselung für API-Keys in der Provider-Registry.

Verwendet Fernet (AES-128-CBC + HMAC-SHA256).
Der Schlüssel wird aus ENCRYPTION_KEY abgeleitet oder – als Fallback –
aus dem ADMIN_MASTER_KEY (Base64-padded SHA-256).
"""
import base64
import hashlib

from cryptography.fernet import Fernet

from app.config import settings


def _derive_key() -> bytes:
    """Leitet einen 32-Byte-Fernet-Key aus den Settings ab."""
    raw = settings.encryption_key or settings.admin_master_key
    digest = hashlib.sha256(raw.encode()).digest()
    return base64.urlsafe_b64encode(digest)


_fernet: Fernet | None = None


def _get_fernet() -> Fernet:
    global _fernet
    if _fernet is None:
        _fernet = Fernet(_derive_key())
    return _fernet


def encrypt_api_key(plaintext: str) -> str:
    """Verschlüsselt einen API-Key für die DB-Speicherung."""
    return _get_fernet().encrypt(plaintext.encode()).decode()


def decrypt_api_key(ciphertext: str) -> str:
    """Entschlüsselt einen API-Key aus der DB."""
    return _get_fernet().decrypt(ciphertext.encode()).decode()
