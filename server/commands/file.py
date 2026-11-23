from .base import Command


class FileCommand(Command):
    def __init__(self):
        super().__init__("file")

    def execute(self, server, client, data: dict) -> None:
        recipient = data.get("to")
        action = data.get("action")
        transfer_id = data.get("transfer_id")

        if not isinstance(recipient, str) or not recipient:
            raise ValueError("Invalid recipient")

        if recipient == client.username:
            raise ValueError("Cannot send files to yourself")

        if not isinstance(transfer_id, str) or not transfer_id:
            raise ValueError("Invalid transfer ID")

        if action not in ("offer", "accept", "reject", "chunk", "end"):
            raise ValueError("Invalid file action")

        packet = {
            "type": "file",
            "action": action,
            "from": client.username,
            "transfer_id": transfer_id
        }

        if action == "offer":
            filename = data.get("filename")
            size = data.get("size")

            if not isinstance(filename, str) or not filename:
                raise ValueError("Invalid filename")

            if type(size) is not int or size < 0:
                raise ValueError("Invalid file size")

            packet["filename"] = filename
            packet["size"] = size

        elif action == "chunk":
            index = data.get("index")
            nonce = data.get("nonce")
            ciphertext = data.get("ciphertext")

            if type(index) is not int or index < 0:
                raise ValueError("Invalid chunk index")

            if not isinstance(nonce, str) or not nonce:
                raise ValueError("Invalid nonce")

            if not isinstance(ciphertext, str) or not ciphertext:
                raise ValueError("Invalid ciphertext")

            packet["index"] = index
            packet["nonce"] = nonce
            packet["ciphertext"] = ciphertext

        if not server.send_to(recipient, packet):
            raise ValueError(f"User '{recipient}' not found")
