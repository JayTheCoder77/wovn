from __future__ import annotations

import base64
import hashlib

from cryptography.fernet import Fernet, InvalidToken

from api.config import settings

FERNET_KEY_ID = "fernet-v1"


def _fernet() -> Fernet:
    digest = hashlib.sha256(settings.secret_key.encode("utf-8")).digest()
    return Fernet(base64.urlsafe_b64encode(digest))


def encrypt_key(plain: str) -> str:
    return _fernet().encrypt(plain.encode("utf-8")).decode("ascii")


def decrypt_key(token: str) -> str:
    try:
        return _fernet().decrypt(token.encode("ascii")).decode("utf-8")
    except InvalidToken as exc:
        raise ValueError("Stored Groq key could not be decrypted. Check WOVN secret key.") from exc
