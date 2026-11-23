import argparse

from server.server import ChatServer
from client.client import ChatClient
from client.terminal import TerminalUI
from client.gui import ChatGUI

def main():
    parser = argparse.ArgumentParser(
        description="End-to-end encrypted TCP chat"
    )

    parser.add_argument(
        "mode",
        choices=["server", "client"],
        help="Run as server or client"
    )

    parser.add_argument(
        "--host",
        default="127.0.0.1",
        help="Server address"
    )

    parser.add_argument(
        "--port",
        type=int,
        default=5000,
        help="Server port"
    )

    parser.add_argument(
        "--gui",
        action="store_true",
        help="Launch the graphical client"
    )

    args = parser.parse_args()

    if args.mode == "server":
        ChatServer(args.host, args.port).start()
    else:
        client = ChatClient(args.host, args.port)

        if args.gui:
            ChatGUI(client).start()
        else:
            TerminalUI(client).start()


if __name__ == "__main__":
    main()
