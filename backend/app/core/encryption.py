import hashlib
import logging
import threading
from base64 import urlsafe_b64encode

from cryptography.fernet import Fernet, InvalidToken

from app.core.config import settings

logger = logging.getLogger(__name__)

_fernet: Fernet | None = None
_fernet_lock = threading.Lock()


def _get_fernet() -> Fernet:
    global _fernet
    if _fernet is None:
        with _fernet_lock:
            if _fernet is None:
                key = hashlib.sha256(settings.SECRET_KEY.encode()).digest()
                _fernet = Fernet(urlsafe_b64encode(key))
    return _fernet


def encrypt_api_key(plaintext: str) -> str:
    return _get_fernet().encrypt(plaintext.encode()).decode()


def decrypt_api_key(ciphertext: str) -> str:
    try:
        return _get_fernet().decrypt(ciphertext.encode()).decode()
    except InvalidToken:
        logger.warning("Key not encrypted (plaintext or wrong key), returning as-is")
        return ciphertext
