import functools

from cryptography.fernet import Fernet, InvalidToken

from src.config.manager import settings


class DataEncryptor:
    """
    Symmetric encryption helper (Fernet / AES-128-CBC + HMAC) used to protect
    sensitive third-party secrets - such as Razorpay OAuth tokens - at rest.
    """

    def __init__(self, key: str):
        if not key:
            raise ValueError(
                "`ENCRYPTION_KEY` is not configured. Generate one with "
                "`python -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())'`."
            )
        self._fernet = Fernet(key.encode("utf-8"))

    def encrypt(self, plaintext: str) -> str:
        return self._fernet.encrypt(plaintext.encode("utf-8")).decode("utf-8")

    def decrypt(self, ciphertext: str) -> str:
        try:
            return self._fernet.decrypt(ciphertext.encode("utf-8")).decode("utf-8")
        except InvalidToken as exc:
            raise ValueError("Unable to decrypt value - wrong key or corrupted ciphertext.") from exc


@functools.lru_cache
def get_data_encryptor() -> DataEncryptor:
    return DataEncryptor(key=settings.ENCRYPTION_KEY)
