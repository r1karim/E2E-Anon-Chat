import json
import socket
import threading
import uuid
from pathlib import Path


from shared.protocol import JsonProtocol
from .peer_session import PeerSession
from .file_transfer import FileTransfer


class ChatClient:
    def __init__(self, host: str = "127.0.0.1", port: int = 5000):
        self.host = host
        self.port = port

        self.socket: socket.socket | None = None
        self.protocol: JsonProtocol | None = None

        self.username: str | None = None
        self.sessions: dict[str, PeerSession] = {}
        self.online_users: set[str] = set()
        self.pending: dict[str, list[tuple]] = {}
        self.transfers: dict[str, FileTransfer] = {}

        self.send_lock = threading.Lock()
        self.session_lock = threading.RLock()
        self.running = False
        self.on_event = None

    def connect(self, username: str) -> None:
        self.socket = socket.create_connection((self.host, self.port))
        self.protocol = JsonProtocol(self.socket)

        self.send({
            "type": "join",
            "username": username
        })

        response = self.protocol.receive()

        if response is None or response.get("type") != "joined":
            self.disconnect()
            raise ConnectionError(
                response.get("message", "Registration failed")
                if response else "Server disconnected"
            )

        self.username = response["username"]
        self.running = True

        threading.Thread(
            target=self._receive_loop,
            daemon=True
        ).start()

    def send(self, data: dict) -> None:
        with self.send_lock:
            if self.protocol is None:
                raise ConnectionError("Not connected")
            self.protocol.send(data)

    def list_users(self) -> None:
        print("Connected users: ")
        for user in self.online_users:
            print(user)

    def send_message(self, recipient: str, message: str, is_global: bool=False) -> None:
        if not message.strip():
            return

        if recipient == self.username:
            raise ValueError("Cannot message yourself")

        with self.session_lock:
            session = self.sessions.get(recipient)

            if session is None:
                session = PeerSession(recipient)
                self.sessions[recipient] = session
                self.pending[recipient] = [(message, is_global)]

                self.send({
                    "type": "key_exchange",
                    "to": recipient,
                    "public_key": session.public_key
                })
                return

            if not session.ready:
                self.pending.setdefault(recipient, []).append(message)
                return

            self._send_encrypted(recipient, message, session, is_global=is_global)


    def _send_encrypted(self,recipient: str,message: str,session: PeerSession, is_global:bool=False) -> None:
        encrypted = session.encrypt(message)

        self.send({
            "type": "chat",
            "to": recipient,
            "is_global":is_global,
            **encrypted
        })

    def _handle_key_exchange(self, data: dict) -> None:
        sender = data["from"]
        public_key = data["public_key"]

        with self.session_lock:
            session = self.sessions.get(sender)

            if session is None:
                session = PeerSession(sender)
                self.sessions[sender] = session

                self.send({
                    "type": "key_exchange",
                    "to": sender,
                    "public_key": session.public_key
                })

            session.establish(public_key)

            messages = self.pending.pop(sender, [])

            for (message, is_global) in messages:
                self._send_encrypted(sender, message, session, is_global=is_global)

            for transfer in list(self.transfers.values()):
                if transfer.peer == sender and transfer.status == "accepted":
                    self._start_file_sending(transfer)

    def _handle_chat(self, data: dict) -> None:
        sender = data["from"]

        with self.session_lock:
            session = self.sessions.get(sender)

            if session is None or not session.ready:
                print(f"\n[Error] No encryption key for {sender}")
                return

            message = session.decrypt(
                data["nonce"],
                data["ciphertext"]
            )

        # emitting event to the gui
        self.emit(
            "message",
            sender=sender,
            message=message,
            is_global=data['is_global']
        )

        print(f"\n({'global' if data['is_global'] else 'private'})[{sender}] {message}\n> ", end="", flush=True)

    def _receive_loop(self) -> None:
        try:
            while self.running:
                data = self.protocol.receive()

                if data is None:
                    break

                message_type = data.get("type")

                if message_type == "key_exchange":
                    self._handle_key_exchange(data)

                elif message_type == "chat":
                    self._handle_chat(data)

                elif message_type == "users":
                    users = data.get("clients", [])

                    with self.session_lock:
                        new_users = {user["name"] for user in users}

                        offline_users = self.online_users - new_users

                        for username in offline_users:
                            self.sessions.pop(username, None)

                            self.pending.pop(username, None)

                        self.online_users = new_users

                        self.emit("users", users=self.online_users)

                elif message_type == "join":
                    user = data.get("username")
                    addr = data.get("ip")

                    if user == self.username:
                        continue

                    print(f"{user} joined from ({addr})\n> ", end="", flush=True)

                elif message_type == "file":
                    self._handle_file(data)


                elif message_type == "error":
                    print(f"\n[Server error] {data.get('message')}\n> ", end="", flush=True)

        except (OSError, ConnectionError, ValueError, json.JSONDecodeError) as e:
            if self.running:
                print(f"\n[Connection error] {e}")

        finally:
            self.disconnect()

    def disconnect(self) -> None:
        self.running = False

        if self.socket is not None:
            try:
                self.socket.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass

            self.socket.close()
            self.socket = None

        self.protocol = None

        with self.session_lock:
            for transfer in self.transfers.values():
                transfer.close()

            self.transfers.clear()

    def send_file(self, recipient: str, filepath: str):
        path = Path(filepath).expanduser()

        if not path.is_file():
            raise ValueError("File does not exist")

        if recipient == self.username:
            raise ValueError("Cannot send files to yourself")

        if recipient not in self.online_users:
            raise ValueError(f"User '{recipient}' is not online")

        transfer_id = uuid.uuid4().hex

        transfer = FileTransfer(
            transfer_id=transfer_id,
            peer=recipient,
            filename=path.name,
            size=path.stat().st_size,
            path=path
        )

        with self.session_lock:
            self.transfers[transfer_id] = transfer

        self.send({
            "type": "file",
            "action": "offer",
            "to": recipient,
            "transfer_id": transfer_id,
            "filename": transfer.filename,
            "size": transfer.size
        })

        print(f"\n[File] Offered {path.name} to {recipient}")
        print(f"[File] Transfer ID: {transfer_id}")

    def accept_file(self, transfer_id: str):
        with self.session_lock:
            transfer = self.transfers.get(transfer_id)

            if transfer is None or transfer.status != "pending":
                raise ValueError("Unknown or inactive file offer")

            if transfer.path is not None:
                raise ValueError("This is an outgoing transfer")

            transfer.start_receiving()

        self.send({
            "type": "file",
            "action": "accept",
            "to": transfer.peer,
            "transfer_id": transfer_id
        })

        print(f"\n[File] Receiving {transfer.filename} from {transfer.peer}")

    def reject_file(self, transfer_id: str):
        with self.session_lock:
            transfer = self.transfers.get(transfer_id)

            if transfer is None or transfer.status != "pending":
                raise ValueError("Unknown or inactive file offer")

            if transfer.path is not None:
                raise ValueError("This is an outgoing transfer")

            transfer.status = "rejected"
            self.transfers.pop(transfer_id)

        self.send({
            "type": "file",
            "action": "reject",
            "to": transfer.peer,
            "transfer_id": transfer_id
        })

        print("\n[File] Transfer rejected")

    def _handle_file(self, data: dict):
        action = data["action"]
        transfer_id = data["transfer_id"]
        sender = data["from"]

        if action == "offer":
            size = data["size"]

            if type(size) is not int or size < 0:
                raise ValueError("Invalid file size")

            filename = data["filename"]

            if not isinstance(filename, str) or not filename:
                raise ValueError("Invalid filename")

            with self.session_lock:
                if transfer_id in self.transfers:
                    raise ValueError("Duplicate transfer ID")

                self.transfers[transfer_id] = FileTransfer(
                    transfer_id=transfer_id,
                    peer=sender,
                    filename=filename,
                    size=size
                )

            self.emit(
                "file_offer",
                sender=sender,
                filename=filename,
                transfer_id=transfer_id,
                size=size
            )

            print(f"\n[File] {sender} wants to send {filename}")
            print(f"[File] Size: {size} bytes")
            print(f"[File] Accept with: /accept {transfer_id}")
            print(f"[File] Reject with: /reject {transfer_id}")
            return

        with self.session_lock:
            transfer = self.transfers.get(transfer_id)

            if transfer is None or transfer.peer != sender:
                raise ValueError("Unknown file transfer")

            if action == "accept":
                if transfer.path is None or transfer.status != "pending":
                    raise ValueError("Invalid file acceptance")

                session = self.sessions.get(sender)

                if session is None:
                    session = PeerSession(sender)
                    self.sessions[sender] = session

                    self.send({
                        "type": "key_exchange",
                        "to": sender,
                        "public_key": session.public_key
                    })

                transfer.status = "accepted"

                if session.ready:
                    self._start_file_sending(transfer)

            elif action == "reject":
                transfer.status = "rejected"
                self.transfers.pop(transfer_id)
                print(f"\n[File] {sender} rejected {transfer.filename}")

            elif action == "chunk":
                if transfer.path is None or transfer.file is None:
                    raise ValueError("File transfer not accepted")

                session = self.sessions.get(sender)

                if session is None or not session.ready:
                    raise ValueError("Encryption session not ready")

                transfer.receive_chunk(
                    data["index"],
                    data["nonce"],
                    data["ciphertext"],
                    session
                )

            elif action == "end":
                if transfer.path is None or transfer.file is None:
                    raise ValueError("File transfer not active")

                transfer.finish_receiving()
                self.transfers.pop(transfer_id)

                print(f"\n[File] Saved: {transfer.path}")

    def _start_file_sending(self, transfer: FileTransfer):
        if transfer.status != "accepted":
            return

        session = self.sessions.get(transfer.peer)

        if session is None or not session.ready:
            return

        transfer.status = "transferring"

        def worker():
            try:
                transfer.send_chunks(session, self.send)
                print(f"\n[File] Sent {transfer.filename} to {transfer.peer}")
            except (OSError, ConnectionError, ValueError, RuntimeError) as e:
                print(f"\n[File] Transfer failed: {e}")
            finally:
                with self.session_lock:
                    self.transfers.pop(transfer.transfer_id, None)

        threading.Thread(target=worker, daemon=True).start()

    def emit(self, event_type: str, **data):
        if self.on_event is not None:
            self.on_event(event_type, data)