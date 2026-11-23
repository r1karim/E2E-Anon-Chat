import tkinter as tk
from tkinter import messagebox, filedialog
import threading, queue
from .client import ChatClient


class ChatGUI:
    def __init__(self, client: ChatClient):
        self.client = client

        self.root = tk.Tk()
        self.root.title("Encrypted TCP Chat")
        self.root.geometry("450x350")
        self.root.resizable(False, False)

        self.events = queue.Queue()
        self.client.on_event = self.queue_event

        self.build_connection_screen()
        self.root.after(50, self.process_events)

    def build_connection_screen(self):
        self.frame = tk.Frame(self.root, padx=40, pady=40)
        self.frame.pack(expand=True, fill="both")

        tk.Label(
            self.frame,
            text="Encrypted TCP Chat",
            font=("Arial", 20, "bold")
        ).pack(pady=(10, 30))

        tk.Label(
            self.frame,
            text="Username:",
            font=("Arial", 11)
        ).pack(anchor="w")

        self.username_entry = tk.Entry(
            self.frame,
            font=("Arial", 12)
        )
        self.username_entry.pack(fill="x", pady=(5, 20))
        self.username_entry.focus()

        self.connect_button = tk.Button(
            self.frame,
            text="Connect",
            font=("Arial", 12),
            command=self.connect
        )
        self.connect_button.pack(fill="x")

        self.username_entry.bind(
            "<Return>",
            lambda event: self.connect()
        )

    def connect(self):
        username = self.username_entry.get().strip()

        if not username:
            messagebox.showerror("Error", "Username cannot be empty")
            return

        self.connect_button.config(state="disabled")

        threading.Thread(
            target=self._connect_worker,
            args=(username,),
            daemon=True
        ).start()

    def _connect_worker(self, username):
        try:
            self.client.connect(username)
        except (OSError, ConnectionError, ValueError) as e:
            self.root.after(0, self._connection_failed, str(e))
            return

        self.root.after(0, self._connection_successful)

    def _connection_failed(self, error):
        self.connect_button.config(state="normal")
        messagebox.showerror("Connection failed", error)

    def _connection_successful(self):
        self.frame.destroy()
        self.build_chat_screen()

    def start(self):
        try:
            self.root.mainloop()
        finally:
            self.client.disconnect()

    def build_chat_screen(self):
        self.root.geometry("900x600")
        self.root.resizable(True, True)

        # Left sidebar
        sidebar = tk.Frame(self.root, width=180, bg="#eeeeee")
        sidebar.pack(side="left", fill="y")
        sidebar.pack_propagate(False)

        tk.Label(
            sidebar,
            text="Conversations",
            font=("Arial", 13, "bold"),
            bg="#eeeeee"
        ).pack(pady=15)

        self.user_list = tk.Listbox(
            sidebar,
            font=("Arial", 11),
            borderwidth=0
        )
        self.user_list.pack(fill="both", expand=True, padx=10, pady=10)

        self.user_list.insert("end", "Global")
        self.user_list.selection_set(0)
        self.user_list.bind("<<ListboxSelect>>", self.select_chat)

        # Right side
        chat_frame = tk.Frame(self.root)
        chat_frame.pack(side="right", fill="both", expand=True)

        self.chat_title = tk.Label(
            chat_frame,
            text="Global Chat",
            font=("Arial", 15, "bold")
        )
        self.chat_title.pack(pady=12)

        self.chat_text = tk.Text(
            chat_frame,
            state="disabled",
            wrap="word",
            font=("Arial", 11)
        )
        self.chat_text.pack(
            fill="both",
            expand=True,
            padx=10,
            pady=5
        )

        bottom = tk.Frame(chat_frame)
        bottom.pack(fill="x", padx=10, pady=10)

        self.message_entry = tk.Entry(
            bottom,
            font=("Arial", 12)
        )
        self.message_entry.pack(
            side="left",
            fill="x",
            expand=True,
            padx=(0, 10)
        )

        self.message_entry.bind(
            "<Return>",
            lambda event: self.send_message()
        )

        tk.Button(
            bottom,
            text="Send",
            command=self.send_message
        ).pack(side="right")

        tk.Button(
            bottom,
            text="File",
            command=self.send_file
        ).pack(side="right", padx=5)

        self.selected_chat = "Global"
        self.messages = {"Global": []}

        self.update_users(self.client.online_users)

    def send_file(self):
        recipient = self.selected_chat

        if recipient == "Global":
            messagebox.showinfo(
                "File transfer",
                "Select a user to send a file."
            )
            return

        filepath = filedialog.askopenfilename(
            title="Select a file to send"
        )

        if not filepath:
            return

        try:
            self.client.send_file(recipient, filepath)
        except (ValueError, OSError, ConnectionError) as e:
            messagebox.showerror("File error", str(e))


    def select_chat(self, event=None):
        selection = self.user_list.curselection()

        if not selection:
            return

        self.selected_chat = self.user_list.get(selection[0])

        self.chat_title.config(
            text="Global Chat"
            if self.selected_chat == "Global"
            else f"Chat with {self.selected_chat}"
        )

        self.refresh_messages()

    def send_message(self):
        message = self.message_entry.get().strip()

        if not message:
            return

        try:
            if self.selected_chat == "Global":
                for user in list(self.client.online_users):
                    if user != self.client.username:
                        self.client.send_message(
                            user,
                            message,
                            is_global=True
                        )
            else:
                self.client.send_message(
                    self.selected_chat,
                    message,
                    is_global=False
                )

        except (ValueError, OSError, ConnectionError) as e:
            messagebox.showerror("Message error", str(e))
            return

        self.add_message(
            self.selected_chat,
            "You",
            message
        )

        self.message_entry.delete(0, "end")

    def add_message(self, chat, sender, message):
        self.messages.setdefault(chat, []).append(
            (sender, message)
        )

        if chat == self.selected_chat:
            self.refresh_messages()

    def refresh_messages(self):
        self.chat_text.config(state="normal")
        self.chat_text.delete("1.0", "end")

        for sender, message in self.messages.get(
                self.selected_chat, []
        ):
            self.chat_text.insert(
                "end",
                f"{sender}: {message}\n\n"
            )

        self.chat_text.config(state="disabled")
        self.chat_text.see("end")

    def update_users(self, users):
        selected = self.selected_chat

        self.user_list.delete(0, "end")
        self.user_list.insert("end", "Global")

        for user in sorted(users):
            if user != self.client.username:
                self.user_list.insert("end", user)

        items = self.user_list.get(0, "end")

        if selected in items:
            index = items.index(selected)
        else:
            index = 0

        self.user_list.selection_set(index)
        self.select_chat()

    def queue_event(self, event_type, data):
        self.events.put((event_type, data))

    def process_events(self):
        while not self.events.empty():
            event_type, data = self.events.get_nowait()

            if event_type == "connection_successful":
                self._connection_successful()

            elif event_type == "connection_failed":
                self._connection_failed(data["error"])

            elif event_type == "message":
                if hasattr(self, "chat_text"):
                    chat = "Global" if data["is_global"] else data["sender"]
                    self.add_message(chat, data["sender"], data["message"])

            elif event_type == "users":
                if hasattr(self, "user_list"):
                    self.update_users(data["users"])

            elif event_type == "file_offer":
                self.show_file_offer(data)

        self.root.after(50, self.process_events)

    def show_file_offer(self, data):
        sender = data["sender"]
        filename = data["filename"]
        transfer_id = data["transfer_id"]
        size = data["size"]

        accepted = messagebox.askyesno(
            "Incoming file",
            f"{sender} wants to send you:\n\n"
            f"{filename}\n"
            f"Size: {size:,} bytes\n\n"
            "Accept this file?"
        )

        try:
            if accepted:
                self.client.accept_file(transfer_id)
            else:
                self.client.reject_file(transfer_id)

        except (ValueError, OSError, ConnectionError) as e:
            messagebox.showerror("File error", str(e))