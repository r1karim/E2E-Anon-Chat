from shared.crypto.diffie_hellman import DiffieHellman
from shared.crypto.aes_cipher import AESCipher


class PeerSession:
    def __init__(self, username: str):
        self.username = username
        self.dh = DiffieHellman()
        self.cipher: AESCipher | None = None

    @property
    def ready(self) -> bool:
        return self.cipher is not None

    @property
    def public_key(self) -> str:
        return str(self.dh.public_key)

    def establish(self, peer_public_key: str) -> None:
        if self.ready:
            return

        shared_secret = self.dh.compute_shared_secret(
            int(peer_public_key)
        )

        self.cipher = AESCipher(shared_secret)

    def encrypt(self, message: str) -> dict:
        if not self.ready:
            raise RuntimeError("Key exchange not completed")

        return self.cipher.encrypt(message)

    def decrypt(self, nonce: str, ciphertext: str) -> str:
        if not self.ready:
            raise RuntimeError("Key exchange not completed")

        return self.cipher.decrypt(nonce, ciphertext)

    def encrypt_bytes(self, data: bytes) -> dict:
        if not self.ready:
            raise RuntimeError("Key exchange not completed")

        return self.cipher.encrypt_bytes(data)

    def decrypt_bytes(self, nonce: str, ciphertext: str) -> bytes:
        if not self.ready:
            raise RuntimeError("Key exchange not completed")

        return self.cipher.decrypt_bytes(nonce, ciphertext)
