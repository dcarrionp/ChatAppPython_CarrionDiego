import socket
import threading
import pickle
from cryptography.fernet import Fernet
import tkinter as tk
from tkinter import scrolledtext, Button, Toplevel
import json
import time
from Client import Cliente

class Servidor:
    def __init__(self, host="localhost", port=4000):
        self.host = host  # Definiendo el atributo host
        self.port = port  # Definiendo el atributo port
        self.clientes = []
        self.key = Fernet.generate_key()
        self.cipher = Fernet(self.key)
        self.mensajes_historicos = self.cargar_mensajes()

        print(f"Clave Fernet generada (copie esto para los clientes): {self.key.decode()}")

        # Initialize server socket
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind((self.host, self.port))  # Usando los atributos host y port
        self.sock.setblocking(False)

        self.running = False

        #Creación de la ventana principal de la GUI
        self.window = tk.Tk()
        self.window.title("Servidor Chat")

        # Estableciendo un estilo visual para la ventana
        self.window.configure(bg='#2D2D2D')  # Color de fondo oscuro

        # Configuración de la fuente
        font_style = ('Arial', 12)
        button_font = ('Arial', 10, 'bold')

        # Área de logs con scroll
        self.log_area = scrolledtext.ScrolledText(self.window, height=20, width=70, state='disabled', bg="#333333", fg="#FFFFFF", font=font_style)
        self.log_area.grid(row=0, column=0, columnspan=3, padx=10, pady=10)

        # Botones para el control del servidor
        self.key_entry = tk.Entry(self.window, fg="blue", width=70)
        self.key_entry.grid(row=2, column=0, columnspan=2, padx=10, pady=5)
        self.key_entry.insert(0, self.key.decode())
        self.key_entry.configure(state='readonly')

        # Botones para el control del servidor
        self.start_button = Button(self.window, text="Iniciar Servidor", command=self.start_server, font=button_font, bg="#4CAF50", fg="white")
        self.start_button.grid(row=1, column=0, padx=10, pady=10, sticky="ew")

        self.join_button = Button(self.window, text="Unirse al Servidor", command=self.launch_client, font=button_font, bg="#2196F3", fg="white")
        self.join_button.grid(row=1, column=1, padx=10, pady=10, sticky="ew")

        self.stop_button = Button(self.window, text="Detener Servidor", command=self.stop_server, state='disabled', font=button_font, bg="#F44336", fg="white")
        self.stop_button.grid(row=1, column=2, padx=10, pady=10, sticky="ew")

        # Finaliza la configuración de la ventana
        self.window.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.window.mainloop()

        self.window.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.window.mainloop()

    def cargar_mensajes(self):
        try:
            with open('historial_mensajes.json', 'r') as file:
                return json.load(file)
        except FileNotFoundError:
            return []
        
    def guardar_mensaje(self, mensaje):
        self.mensajes_historicos.append(mensaje)
        with open('historial_mensajes.json', 'w') as file:
            json.dump(self.mensajes_historicos, file)

    def log_message(self, message):
        self.log_area.configure(state='normal')
        self.log_area.insert(tk.END, message + "\n")
        self.log_area.yview(tk.END)
        self.log_area.configure(state='disabled')

    def start_server(self):
        if not self.running:
            # Crear un nuevo socket si el anterior fue cerrado
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.sock.bind((self.host, self.port))
            self.sock.setblocking(False)

            self.sock.listen(10)
            self.log_message("Servidor iniciado. Esperando conexiones...")
            self.running = True
            self.start_button.config(state='disabled')
            self.stop_button.config(state='normal')
            threading.Thread(target=self.aceptarCon, daemon=True).start()
            threading.Thread(target=self.procesarCon, daemon=True).start()

    def stop_server(self):
        if self.running:
            self.running = False
            # Cerrar el socket actual
            self.sock.close()
            self.log_message("Servidor detenido.")
            self.start_button.config(state='normal')
            self.stop_button.config(state='disabled')
            # Limpiar la lista de clientes
            self.clientes = []

    def on_closing(self):
        self.stop_server()
        self.window.destroy()

    def aceptarCon(self):
        while self.running:
            try:
                conn, addr = self.sock.accept()
                conn.setblocking(False)
                self.clientes.append(conn)
                self.log_message(f"Conexión aceptada desde {addr}")
                self.enviar_historial(conn)
            except socket.error:
                # Manejar errores típicos, como 'blocking io operation', etc.
                pass
            except Exception as e:
                # Otros errores
                print(f"Error: {e}")

    def procesarCon(self):
        while self.running:
            to_remove = []
            for c in self.clientes:
                try:
                    data = c.recv(1024)
                    if data:
                        decrypted_msg = self.cipher.decrypt(pickle.loads(data))
                        mensaje_texto = decrypted_msg.decode()
                        self.guardar_mensaje(mensaje_texto)
                        self.log_message(f"Mensaje de {c.getpeername()}: {mensaje_texto}")
                        self.msg_to_all(data, c)
                except socket.error:
                    pass
                except Exception as e:
                    to_remove.append(c)
                    print(f"Error: {e}")
            for c in to_remove:
                self.clientes.remove(c)


    def msg_to_all(self, msg, cliente):
        for c in self.clientes:
            if c != cliente:
                try:
                    c.send(msg)
                except:
                    self.clientes.remove(c)

    def enviar_historial(self, conn):
        for mensaje in self.mensajes_historicos:
            mensaje_enc = self.cipher.encrypt(mensaje.encode())
            try:
                conn.send(pickle.dumps(mensaje_enc))
                time.sleep(0.1)  # Pequeña pausa para evitar saturación
            except Exception as e:
                print(f"No se pudo enviar el historial: {e}")
                break

    def launch_client(self):
        # Inicia una nueva ventana del cliente
        client_window = Toplevel(self.window)
        Cliente(host="localhost", port=4000, master=client_window)
if __name__ == "__main__":
    Servidor()