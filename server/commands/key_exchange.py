from .base import Command


class KeyExchangeCommand(Command):
    def __init__(self):
        super().__init__("key_exchange")

    def execute(self, server, client, data: dict) -> None:
        recipient = data.get("to")
        public_key = data.get("public_key")

        if not isinstance(recipient, str) or not recipient:
            raise ValueError("Invalid recipient")

        if not isinstance(public_key, str) or not public_key:
            raise ValueError("Invalid public key")

        if recipient == client.username:
            raise ValueError("Cannot exchange keys with yourself")

        success = server.send_to(recipient, {
            "type": "key_exchange",
            "from": client.username,
            "public_key": public_key
        })



        if not success:
            raise ValueError(f"User '{recipient}' not found")
