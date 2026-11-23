from .base import Command


class ChatCommand(Command):
    def __init__(self):
        super().__init__("chat")

    def execute(self, server, client, data: dict) -> None:
        recipient = data.get("to")
        nonce = data.get("nonce")
        ciphertext = data.get("ciphertext")
        is_global = data.get("is_global")

        if not isinstance(recipient, str) or not recipient:
            raise ValueError("Invalid recipient")

        if not isinstance(nonce, str) or not nonce:
            raise ValueError("Invalid nonce")

        if not isinstance(ciphertext, str) or not ciphertext:
            raise ValueError("Invalid ciphertext")

        if not isinstance(is_global, bool):
            raise ValueError("Invalid is_global")

        if recipient == client.username:
            raise ValueError("Cannot send messages to yourself")

        success = server.send_to(recipient, {
            "type": "chat",
            "from": client.username,
            "nonce": nonce,
            "ciphertext": ciphertext,
            "is_global": is_global
        })

        print(f"{client.username} sent the following text: [{ciphertext}] to {recipient}.")

        if not success:
            raise ValueError(f"User '{recipient}' not found")
