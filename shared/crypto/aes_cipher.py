import base64
import os

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.hazmat.primitives import hashes


class AESCipher:
    def __init__(self, shared_secret: int):
        secret_bytes = shared_secret.to_bytes(
            (shared_secret.bit_length() + 7) // 8,
            byteorder="big"
        )

        self.key = HKDF(
            algorithm=hashes.SHA256(),
            length=32,
            salt=None,
            info=b"tcp-chat-aes-key"
        ).derive(secret_bytes)

        self.aes = AESGCM(self.key)

    def encrypt_bytes(self, data: bytes) -> dict:
        nonce = os.urandom(12)

        ciphertext = self.aes.encrypt(
            nonce,
            data,
            None
        )

        return {
            "nonce": base64.b64encode(nonce).decode("ascii"),
            "ciphertext": base64.b64encode(ciphertext).decode("ascii")
        }

    def decrypt_bytes(self, nonce: str, ciphertext: str) -> bytes:
        nonce_bytes = base64.b64decode(nonce, validate=True)
        ciphertext_bytes = base64.b64decode(ciphertext, validate=True)

        return self.aes.decrypt(
            nonce_bytes,
            ciphertext_bytes,
            None
        )


    def encrypt(self, message: str) -> dict:
        nonce = os.urandom(12)

        ciphertext = self.aes.encrypt(
            nonce,
            message.encode("utf-8"),
            None
        )

        return {
            "nonce": base64.b64encode(nonce).decode("utf-8"),
            "ciphertext": base64.b64encode(ciphertext).decode("utf-8")
        }

    def decrypt(self, nonce: str, ciphertext: str) -> str:
        nonce_bytes = base64.b64decode(nonce, validate=True)
        ciphertext_bytes = base64.b64decode(ciphertext, validate=True)

        plaintext = self.aes.decrypt(
            nonce_bytes,
            ciphertext_bytes,
            None
        )

        return plaintext.decode("utf-8")
