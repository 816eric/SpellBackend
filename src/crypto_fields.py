"""Field-level encryption for PII stored in SQLite (email, phone).

Fernet (AES-128-CBC + HMAC). Key comes from DATA_ENCRYPTION_KEY (any string;
set it as a Fly secret so it is NOT stored beside the database). If unset, a
key is derived from the persisted auth secret - convenient, but then the key
lives on the same volume as the data, so set the env var in production.
Values written before encryption was enabled are read as-is and encrypted by
`encrypt_existing_pii()` at startup.
"""
import base64
import hashlib
import os

from cryptography.fernet import Fernet, InvalidToken
from sqlalchemy.types import String, TypeDecorator

_PREFIX = "enc1:"
_fernet = None


def _get():
    global _fernet
    if _fernet is None:
        material = os.getenv("DATA_ENCRYPTION_KEY")
        if not material:
            from src.security import _secret

            material = "pii:" + _secret().decode()
        key = base64.urlsafe_b64encode(hashlib.sha256(material.encode()).digest())
        _fernet = Fernet(key)
    return _fernet


def encrypt(value):
    if value is None or value == "" or str(value).startswith(_PREFIX):
        return value
    return _PREFIX + _get().encrypt(str(value).encode()).decode()


def decrypt(value):
    if not value or not str(value).startswith(_PREFIX):
        return value  # legacy plaintext
    try:
        return _get().decrypt(str(value)[len(_PREFIX):].encode()).decode()
    except InvalidToken:
        return ""  # wrong key: never leak ciphertext to clients


class EncryptedString(TypeDecorator):
    impl = String
    cache_ok = True

    def process_bind_param(self, value, dialect):
        return encrypt(value)

    def process_result_value(self, value, dialect):
        return decrypt(value)


def encrypt_existing_pii(engine):
    """Startup migration: encrypt legacy plaintext email/phone in place."""
    from sqlalchemy import text

    with engine.begin() as conn:
        rows = conn.execute(text("SELECT id, email, phone FROM user")).fetchall()
        n = 0
        for uid, email, phone in rows:
            ne, np_ = encrypt(email), encrypt(phone)
            if ne != email or np_ != phone:
                conn.execute(
                    text("UPDATE user SET email=:e, phone=:p WHERE id=:i"),
                    {"e": ne, "p": np_, "i": uid},
                )
                n += 1
        if n:
            print(f"Encrypted PII for {n} user(s)")
