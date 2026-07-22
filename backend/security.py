from pwdlib import PasswordHash


# Use pwdlib's recommended Argon2 configuration for new password hashes.
password_hasher = PasswordHash.recommended()


def hash_password(password: str) -> str:
    """Return an irreversible Argon2 hash for a submitted password."""

    # Hash the plaintext before it is written to the database.
    return password_hasher.hash(password)
