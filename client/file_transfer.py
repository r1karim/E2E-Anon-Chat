from pathlib import Path


class FileTransfer:
    CHUNK_SIZE = 64 * 1024  # 64 KB

    def __init__(
        self,
        transfer_id: str,
        peer: str,
        filename: str,
        size: int,
        path: Path | None = None
    ):
        self.transfer_id = transfer_id
        self.peer = peer
        self.filename = filename
        self.size = size
        self.path = path

        self.transferred_bytes = 0
        self.next_index = 0
        self.status = "pending"
        self.file = None

    def send_chunks(self, session, send):
        """Read, encrypt, and send a file in chunks."""
        self.status = "transferring"

        try:
            with open(self.path, "rb") as file:
                while chunk := file.read(self.CHUNK_SIZE):
                    encrypted = session.encrypt_bytes(chunk)

                    send({
                        "type": "file",
                        "action": "chunk",
                        "to": self.peer,
                        "transfer_id": self.transfer_id,
                        "index": self.next_index,
                        **encrypted
                    })

                    self.transferred_bytes += len(chunk)
                    self.next_index += 1

            send({
                "type": "file",
                "action": "end",
                "to": self.peer,
                "transfer_id": self.transfer_id
            })

            self.status = "completed"

        except Exception:
            self.status = "failed"
            raise

    def start_receiving(self):
        """Save received files under client/<sender_username>/."""

        client_dir = Path.cwd()

        # Sanitize the sender's username for use as a folder name.
        safe_user = "".join(
            c for c in self.peer
            if c.isalnum() or c in ("-", "_")
        )

        if not safe_user:
            raise ValueError("Invalid sender username")

        download_dir = Path.cwd() / "transmitted_files" / safe_user
        download_dir.mkdir(parents=True, exist_ok=True)

        safe_name = self.filename.replace("\\", "/").split("/")[-1]

        if not safe_name or safe_name in (".", ".."):
            raise ValueError("Invalid filename")

        # Prefix with transfer ID to avoid overwriting existing files.
        self.path = download_dir / f"{self.transfer_id}_{safe_name}"

        self.file = open(self.path, "xb")
        self.status = "transferring"

    def receive_chunk(self, index: int, nonce: str, ciphertext: str, session):
        """Decrypt and write one chunk."""
        if self.status != "transferring" or self.file is None:
            raise RuntimeError("Transfer is not active")

        if index != self.next_index:
            raise ValueError("Unexpected chunk index")

        chunk = session.decrypt_bytes(nonce, ciphertext)

        if len(chunk) > self.CHUNK_SIZE:
            raise ValueError("Chunk exceeds maximum size")

        if self.transferred_bytes + len(chunk) > self.size:
            raise ValueError("File exceeds announced size")

        self.file.write(chunk)

        self.transferred_bytes += len(chunk)
        self.next_index += 1

    def finish_receiving(self):
        """Finish only if the expected number of bytes arrived."""
        if self.status != "transferring" or self.file is None:
            raise RuntimeError("Transfer is not active")

        if self.transferred_bytes != self.size:
            raise ValueError("Incomplete file transfer")

        self.file.close()
        self.file = None
        self.status = "completed"

    def close(self):
        if self.file is not None:
            self.file.close()
            self.file = None
