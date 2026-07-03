from datetime import timedelta

import pytest

from src.core.security import create_access_token, decode_token, hash_password
from src.core.security import verify_password


def test_hash_password_verifies_original_password() -> None:
    password_hash = hash_password("correct-horse-battery-staple")

    assert password_hash != "correct-horse-battery-staple"
    assert verify_password("correct-horse-battery-staple", password_hash)


def test_verify_password_rejects_wrong_password() -> None:
    password_hash = hash_password("correct-horse-battery-staple")

    assert not verify_password("wrong-password", password_hash)


def test_verify_password_rejects_invalid_hash() -> None:
    assert not verify_password("password", "not-a-valid-argon2-hash")


def test_create_access_token_sets_subject() -> None:
    token = create_access_token("user-id")

    assert decode_token(token)["sub"] == "user-id"


def test_decode_token_rejects_expired_token() -> None:
    token = create_access_token("user-id", expires_delta=timedelta(seconds=-1))

    with pytest.raises(ValueError):
        decode_token(token)
