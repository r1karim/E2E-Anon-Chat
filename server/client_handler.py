import json
import socket
import threading

from shared.protocol import JsonProtocol
from .commands import Command


class ClientHandler:
    def __init__(
        self,
        server,
        conn: socket.socket,
        addr: tuple
    ):
        self.server = server
        self.conn = conn
        self.addr = addr

        self.username: str | None = None
        self.protocol = JsonProtocol(conn)

        self.send_lock = threading.Lock()

    def run(self) -> None:
        try:
            if not self.register():
                return

            while True:
                try:
                    data = self.protocol.receive()

                    if data is None:
                        break

                    if data.get("type") == "quit":
                        break

                    command = Command.get(data.get("type"))

                    if command is None:
                        return

                    command.execute(self.server, self, data)

                except (ValueError, json.JSONDecodeError) as e:
                    self.send({
                        "type": "error",
                        "message": str(e)
                    })

        except (OSError, ConnectionError):
            pass

        finally:
            self.disconnect()

    def register(self) -> bool:
        data = self.protocol.receive()

        if data is None or data.get("type") != "join":
            self.send({
                "type": "error",
                "message": "Expected a join request"
            })
            return False

        username = data.get("username")

        if not isinstance(username, str) or not username.strip():
            self.send({
                "type": "error",
                "message": "Invalid username"
            })
            return False

        self.username = username.strip()

        if not self.server.add_client(self):
            self.send({
                "type": "error",
                "message": "Username already taken"
            })
            return False

        self.send({
            "type": "joined",
            "username": self.username
        })

        print(f"{self.username} connected from {self.addr}")

        self.server.broadcast({
            "type": "join",
            "username": self.username,
            "ip": self.addr
        })
        self.server.notify_users()

        return True

    def send(self, data: dict) -> None:
        with self.send_lock:
            self.protocol.send(data)

    def disconnect(self) -> None:
        self.server.remove_client(self)

        try:
            self.conn.shutdown(socket.SHUT_RDWR)
        except OSError:
            pass

        self.conn.close()

        if self.username:
            print(f"{self.username} disconnected")
            self.server.notify_users()
