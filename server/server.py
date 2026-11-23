import socket
import threading

from .client_handler import ClientHandler


class ChatServer:
    def __init__(self, host: str = "127.0.0.1", port: int = 5000):
        self.host = host
        self.port = port

        self.clients: dict[str, ClientHandler] = {}
        self.lock = threading.Lock()

        self.socket = socket.socket(
            socket.AF_INET,
            socket.SOCK_STREAM
        )

        self.socket.setsockopt(
            socket.SOL_SOCKET,
            socket.SO_REUSEADDR,
            1
        )

        self.running = False

    def start(self) -> None:
        self.socket.bind((self.host, self.port))
        self.socket.listen()

        self.running = True
        print(f"Server listening on {self.host}:{self.port}")

        try:
            while self.running:
                conn, addr = self.socket.accept()

                handler = ClientHandler(
                    server=self,
                    conn=conn,
                    addr=addr
                )

                threading.Thread(
                    target=handler.run,
                    daemon=True
                ).start()

        except (KeyboardInterrupt, OSError):
            pass

        finally:
            self.stop()

    def add_client(self, client: ClientHandler) -> bool:
        with self.lock:
            if not client.username or client.username in self.clients:
                return False

            self.clients[client.username] = client

            return True

    def remove_client(self, client: ClientHandler) -> None:
        with self.lock:
            if self.clients.get(client.username) is client:
                del self.clients[client.username]

    def get_client(self, username: str) -> ClientHandler | None:
        with self.lock:
            return self.clients.get(username)

    def list_clients(self) -> list[dict]:
        with self.lock:
            return [
                {
                    "name": client.username,
                    "ip": client.addr[0],
                    "port": client.addr[1]
                }
                for client in self.clients.values()
            ]

    def broadcast(
        self,
        message: dict,
        exclude: ClientHandler | None = None
    ) -> None:
        with self.lock:
            recipients = list(self.clients.values())

        for client in recipients:
            if client is exclude:
                continue

            try:
                client.send(message)
            except OSError:
                self.remove_client(client)
                client.disconnect()

    def send_to(self, username: str, message: dict) -> bool:
        client = self.get_client(username)

        if client is None:
            return False

        try:
            client.send(message)
            return True

        except OSError:
            self.remove_client(client)
            client.disconnect()
            return False

    def stop(self) -> None:
        if not self.running:
            return

        self.running = False
        self.socket.close()

        with self.lock:
            clients = list(self.clients.values())
            self.clients.clear()

        for client in clients:
            client.disconnect()

        print("Server stopped.")

    def notify_users(self) -> None:
        self.broadcast({
            "type": "users",
            "clients": self.list_clients()
        })

