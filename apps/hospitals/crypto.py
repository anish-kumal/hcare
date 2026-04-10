from cryptography.fernet import Fernet, InvalidToken
from django.conf import settings


KHALTI_KEY_PREFIX = "khalti:v1:"


def _cipher() -> Fernet:
    """Build Fernet cipher from configured field encryption key."""
    return Fernet(settings.FIELD_ENCRYPTION_KEY.encode("utf-8"))


def encrypt_khalti_key(raw_key: str) -> str:
    """Encrypt a Khalti key with app-level crypto before saving."""
    value = (raw_key or "").strip()
    if not value:
        return ""
    if value.startswith(KHALTI_KEY_PREFIX):
        return value

    token = _cipher().encrypt(value.encode("utf-8")).decode("utf-8")
    return f"{KHALTI_KEY_PREFIX}{token}"


def decrypt_khalti_key(stored_value: str) -> str:
    """
    Decrypt a previously encrypted Khalti key.

    Backward compatibility: if the prefix is missing, return the value as-is.
    """
    value = (stored_value or "").strip()
    if not value:
        return ""
    if not value.startswith(KHALTI_KEY_PREFIX):
        return value

    token = value[len(KHALTI_KEY_PREFIX):]
    try:
        return _cipher().decrypt(token.encode("utf-8")).decode("utf-8")
    except (InvalidToken, ValueError) as exc:
        raise ValueError("Invalid encrypted Khalti key.") from exc
