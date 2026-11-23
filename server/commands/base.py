from abc import ABC, abstractmethod

class Command(ABC):
    registry: dict[str, "Command"] = {}

    def __init__(self, name: str):
        if name in Command.registry:
            raise ValueError(f"Command '{name}' already registered")

        self.name = name
        Command.registry[name] = self

    @abstractmethod
    def execute(self, server, client, data: dict) -> None:
        pass

    @classmethod
    def get(cls, name: str) -> "Command | None":
        return cls.registry.get(name)
