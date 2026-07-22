from pwdlib import PasswordHash


# Use pwdlib's recommended Argon2 configuration for new password hashes.
password_hasher = PasswordHash.recommended()


def hash_password(password: str) -> str:
    """Return an irreversible Argon2 hash for a submitted password."""

    # Hash the plaintext before it is written to the database.
    return password_hasher.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    """Verify a submitted password against its stored Argon2 hash."""

    # Delegate constant-time hash verification to the password library.
    return password_hasher.verify(password, password_hash)
