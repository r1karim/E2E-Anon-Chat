import json
import socket


class JsonProtocol:
    def __init__(self, conn: socket.socket):
        self.conn = conn
        self.reader = conn.makefile("rb")

    def send(self, data: dict) -> None:
        message = json.dumps(data) + "\n"
        self.conn.sendall(message.encode("utf-8"))

    def receive(self) -> dict | None:
        line = self.reader.readline()

        if not line:
            return None

        data = json.loads(line.decode("utf-8"))

        if not isinstance(data, dict):
            raise ValueError("Expected a JSON object")

        return data

    def close(self) -> None:
        self.reader.close()
