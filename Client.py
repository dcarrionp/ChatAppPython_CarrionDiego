import json
import socket
import threading
import pickle
import tkinter as tk
from tkinter import scrolledtext, Label, Entry, Button, messagebox
from tkinter import PhotoImage
from PIL import Image, ImageTk
from cryptography.fernet import Fernet
import random
import time


class LoginDialog:
    def __init__(self, parent):
        self.top = tk.Toplevel(parent)
        self.top.title("Iniciar Sesión")
        self.top.configure(bg="#2D2D2D")
        
        Label(self.top, text="Nombre de Usuario:", bg="#2D2D2D", fg="#FFFFFF", font=("Arial", 12)).grid(row=0, column=0, padx=10, pady=10)
        self.username_entry = Entry(self.top)
        self.username_entry.grid(row=0, column=1, padx=10, pady=10)
        
        Label(self.top, text="Clave Fernet:", bg="#2D2D2D", fg="#FFFFFF", font=("Arial", 12)).grid(row=1, column=0, padx=10, pady=10)
        self.key_entry = Entry(self.top)
        self.key_entry.grid(row=1, column=1, padx=10, pady=10)
        
        self.submit_button = Button(self.top, text="Confirmar", command=self.submit, bg="#0078D4", fg="white", font=("Arial", 12))
        self.submit_button.grid(row=2, column=1, pady=10)
        
        self.username = None
        self.key = None

    def submit(self):
        self.username = self.username_entry.get()
        self.key = self.key_entry.get()
        if not self.username or not self.key:
            messagebox.showwarning("Advertencia", "Nombre de usuario y clave Fernet son requeridos")
        else:
            self.top.destroy()


class Cliente:
    def __init__(self, host="localhost", port=4000, master=None):
        self.host = host
        self.port = port
        self.master = master
        self.setup_ui()
        self.connect_to_server()

    def setup_ui(self):
        self.root = self.master if self.master else tk.Tk()
        self.root.title("Cliente Chat")
        self.root.configure(bg="#2D2D2D")
        style_font = ('Arial', 12)

        # Login Dialog
        login_dialog = LoginDialog(self.root)
        self.root.wait_window(login_dialog.top)

        self.username = login_dialog.username
        if not self.username:
            self.root.destroy()
            return

        self.key = login_dialog.key
        if not self.key:
            self.root.destroy()
            return

        self.cipher = Fernet(self.key.encode())

        # Chat area
        self.msg_area = scrolledtext.ScrolledText(self.root, height=20, width=50, state='disabled', bg="#333333", fg="#FFFFFF", font=style_font)
        self.msg_area.grid(row=0, column=0, padx=10, pady=10, columnspan=2)
        self.msg_area.tag_configure('sent', justify='right')
        self.msg_area.tag_configure('received', justify='left')

        # Message entry
        self.msg_entry = Entry(self.root, width=48, bg="#222222", fg="#FFFFFF", font=style_font)
        self.msg_entry.grid(row=1, column=0, padx=10, pady=10)

        # Send button with icon
        image = Image.open("send_icon.png").resize((30, 30))  # Resize the icon for better fit
        photo = ImageTk.PhotoImage(image)
        self.send_button = Button(self.root, image=photo, command=self.send_msg_button, bg="#2D2D2D", borderwidth=0)
        self.send_button.image = photo  # Keep a reference
        self.send_button.grid(row=1, column=1, padx=10, pady=10)

        if not self.master:
            self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
            self.root.mainloop()

    def connect_to_server(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        while True:
            try:
                self.sock.connect((self.host, self.port))
                threading.Thread(target=self.msg_recv, daemon=True).start()
                break
            except Exception as e:
                time.sleep(5)  # Wait before retrying

    def send_msg_event(self, event):
        self.send_msg()

    def send_msg_button(self):
        self.send_msg()

    def send_msg(self):
        msg = self.msg_entry.get()
        if msg:
            try:
                full_msg = f"{self.username}: {msg}"
                encrypted_msg = pickle.dumps(self.cipher.encrypt(full_msg.encode()))
                self.sock.send(encrypted_msg)
                self.msg_area.configure(state='normal')
                self.msg_area.insert(tk.END, f"{msg}\n", 'sent')
                self.msg_area.yview(tk.END)
                self.msg_area.configure(state='disabled')
                self.msg_entry.delete(0, tk.END)
            except socket.error:
                messagebox.showwarning("Conexión perdida", "Reconectando...")
                self.connect_to_server()
                self.send_msg()

    def msg_recv(self):
        while True:
            try:
                data = self.sock.recv(1024)
                if data:
                    encrypted_message = pickle.loads(data)
                    message = self.cipher.decrypt(encrypted_message).decode()
                    self.display_message(message, 'received')
            except Exception as e:
                print(f"Error: {e}")
                self.reconnect()
                break

    def display_message(self, message, tag):
        self.msg_area.configure(state='normal')
        self.msg_area.insert(tk.END, f"{message}\n", tag)
        self.msg_area.yview(tk.END)
        self.msg_area.configure(state='disabled')

    def on_closing(self):
        try:
            self.sock.send(pickle.dumps(self.cipher.encrypt("Un cliente se ha desconectado.".encode())))
        finally:
            self.sock.close()
            self.root.destroy()


if __name__ == "__main__":
    Cliente()
