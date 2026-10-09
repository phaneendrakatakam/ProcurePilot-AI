from app.core.security import (
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)


def test_password_hashing_round_trip() -> None:
    password = "A-Strong-Test-Password-123"
    password_hash = hash_password(password)
    assert password_hash != password
    assert verify_password(password, password_hash) is True
    assert verify_password("wrong-password", password_hash) is False


def test_access_token_round_trip() -> None:
    token = create_access_token(
        subject="12345678-1234-5678-1234-567812345678",
        roles=["ADMINISTRATOR"],
        permissions=["users.read"],
        expires_minutes=5,
    )
    payload = decode_access_token(token)
    assert payload["sub"] == "12345678-1234-5678-1234-567812345678"
    assert "ADMINISTRATOR" in payload["roles"]
    assert "users.read" in payload["permissions"]
