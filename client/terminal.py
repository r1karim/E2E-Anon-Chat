from .client import ChatClient


class TerminalUI:
    def __init__(self, client: ChatClient):
        self.client = client

    def start(self) -> None:
        username = input("Enter username: ").strip()

        if not username:
            print("Username cannot be empty.")
            return

        try:
            self.client.connect(username)
        except (OSError, ConnectionError) as e:
            print(f"Connection failed: {e}")
            return

        print(f"\nConnected as {self.client.username}")
        self.show_help()

        try:
            while self.client.running:
                text = input("\n> ").strip()

                if not text:
                    continue

                if text[0] != "/":
                    self.handle_global_message(text)

                if text == "/quit":
                    break

                elif text == "/list":
                    self.client.list_users()

                elif text == "/help":
                    self.show_help()

                elif text.startswith("/msg"):
                    self.handle_private_message(text)

                elif text.startswith("/file"):
                    self.handle_file(text)

                elif text.startswith("/accept"):
                    self.handle_accept(text)

                elif text.startswith("/reject"):
                    self.handle_reject(text)


        except (KeyboardInterrupt, EOFError):
            pass

        finally:
            self.client.disconnect()
            print("\nDisconnected.")

    def handle_private_message(self, text: str) -> None:
        parts = text.split(maxsplit=2)

        if len(parts) < 3:
            print("Usage: /msg <username> <message>")
            return

        recipient = parts[1]
        message = parts[2]

        try:
            self.client.send_message(recipient, message)
        except (ValueError, ConnectionError, OSError) as e:
            print(f"Error: {e}")

    def handle_global_message(self, text:str) -> None:
        for user in self.client.online_users:
            if user == self.client.username:
                continue

            try:
                self.client.send_message(user, text, is_global=True)
            except (ValueError, ConnectionError, OSError) as e:
                print(f"Error: {e}")

    def show_help(self) -> None:
        print("\nAvailable commands:")
        print("  /msg <username> <message>  Send a private message")
        print("  /file <username> <path>    Offer a file")
        print("  /accept <transfer_id>     Accept a file")
        print("  /reject <transfer_id>     Reject a file")
        print("  /list                     Show connected users")
        print("  /help                     Show this help")
        print("  /quit                     Disconnect")
        print("  <message>                 Send a global message")

    def handle_file(self, text: str):
        parts = text.split(maxsplit=2)

        if len(parts) < 3:
            print("Usage: /file <username> <filepath>")
            return

        recipient = parts[1]
        filepath = parts[2]

        try:
            self.client.send_file(recipient, filepath)
        except (ValueError, OSError, ConnectionError) as e:
            print(f"[File error] {e}")

    def handle_accept(self, text: str):
        parts = text.split(maxsplit=1)

        if len(parts) != 2:
            print("Usage: /accept <transfer_id>")
            return

        try:
            self.client.accept_file(parts[1])
        except (ValueError, OSError, ConnectionError) as e:
            print(f"[File error] {e}")

    def handle_reject(self, text: str):
        parts = text.split(maxsplit=1)

        if len(parts) != 2:
            print("Usage: /reject <transfer_id>")
            return

        try:
            self.client.reject_file(parts[1])
        except (ValueError, OSError, ConnectionError) as e:
            print(f"[File error] {e}")
