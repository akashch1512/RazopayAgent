import secrets

from pwdlib import PasswordHash

from src.config.manager import settings


class HashGenerator:
    def __init__(self):
        self._hash_ctx = PasswordHash.recommended()
        self._hash_ctx_salt: str = settings.HASHING_SALT

    @property
    def _get_hashing_salt(self) -> str:
        return self._hash_ctx_salt

    @property
    def generate_password_salt_hash(self) -> str:
        """
        A function to generate a hash from Bcrypt to append to the user password.
        """
        return secrets.token_urlsafe(16)

    def generate_password_hash(self, hash_salt: str, password: str) -> str:
        """
        A function that adds the user's password with the layer 1 Bcrypt hash, before
        hash it for the second time using Argon2 algorithm.
        """
        return self._hash_ctx.hash(hash_salt + password)

    def is_password_verified(self, password: str, hashed_password: str) -> bool:
        """
        A function that decodes users' password and verifies whether it is the correct password.
        """
        return self._hash_ctx.verify(password, hashed_password)


def get_hash_generator() -> HashGenerator:
    return HashGenerator()


hash_generator: HashGenerator = get_hash_generator()
