from .base import Command

class ListUsersCommand(Command):
    def __init__(self):
        super().__init__("list")

    def execute(self, server, client, data: dict):
        client.send({
            "type": "users",
            "clients": server.list_clients()
        })