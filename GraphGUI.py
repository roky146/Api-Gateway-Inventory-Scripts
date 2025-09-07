import tkinter as tk
from tkinter import ttk, filedialog, messagebox, font as tkfont
import ttkbootstrap as tb
import threading
import requests
import json
import csv
import os
import time
from datetime import datetime
from PIL import Image, ImageTk  # pip install pillow

# Desactivar warnings SSL
requests.packages.urllib3.disable_warnings()

# Temas disponibles en ttkbootstrap
VALID_THEMES = ["cosmo","flatly","journal","litera","lumen","minty",
                "pulse","sandstone","superhero","vapor","darkly","cyborg"]

class GraphPyGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("GraphPy GUI Rev4 - Inventario APIGW V11 by Marcos R.")
        self.root.geometry("1000x700")
        self.root.tk.call("tk", "scaling", 1.75)

        # --- Tema ttkbootstrap ---
        self.style_name = "cosmo"
        self.style = tb.Style(self.style_name)

        console_font = tkfont.Font(family="Consolas", size=10)

        # --- Frame superior (inputs) ---
        frame_inputs = ttk.LabelFrame(root, text="Configuración de conexión", padding=10)
        frame_inputs.pack(fill="x", padx=10, pady=5)

        # --- Logo ---
        try:
            logo_img = Image.open("logo.png").resize((100,100), Image.ANTIALIAS)
            self.logo_photo = ImageTk.PhotoImage(logo_img)
            lbl_logo = ttk.Label(frame_inputs, image=self.logo_photo)
            lbl_logo.grid(row=0, column=0, columnspan=3, pady=5)
        except Exception:
            pass  # No muestra logo si no hay archivo

        # --- Inputs ---
        ttk.Label(frame_inputs, text="Host/IP con puerto:").grid(row=1, column=0, sticky="e")
        self.entry_host = ttk.Entry(frame_inputs, width=40)
        self.entry_host.grid(row=1, column=1, padx=5, pady=2)

        ttk.Label(frame_inputs, text="Usuario:").grid(row=2, column=0, sticky="e")
        self.entry_user = ttk.Entry(frame_inputs, width=40)
        self.entry_user.grid(row=2, column=1, padx=5, pady=2)

        ttk.Label(frame_inputs, text="Contraseña:").grid(row=3, column=0, sticky="e")
        self.entry_pass = ttk.Entry(frame_inputs, show="*", width=40)
        self.entry_pass.grid(row=3, column=1, padx=5, pady=2)

        ttk.Label(frame_inputs, text="Carpetas raíz (; separadas):").grid(row=4, column=0, sticky="e")
        self.entry_folders = ttk.Entry(frame_inputs, width=40)
        self.entry_folders.grid(row=4, column=1, padx=5, pady=2)

        ttk.Label(frame_inputs, text="Archivo CSV:").grid(row=5, column=0, sticky="e")
        self.entry_csv = ttk.Entry(frame_inputs, width=30)
        self.entry_csv.grid(row=5, column=1, sticky="w", padx=5, pady=2)

        # Botón para seleccionar CSV
        self.btn_choose_csv = tb.Button(frame_inputs, text="Seleccionar...", bootstyle="secondary", command=self.choose_csv)
        self.btn_choose_csv.grid(row=5, column=2, padx=5, pady=2)

        # --- Frame botones (debajo de inputs) ---
        frame_buttons = ttk.Frame(root)
        frame_buttons.pack(fill="x", padx=10, pady=5)

        self.btn_test = tb.Button(frame_buttons, text="Probar conexión", bootstyle="info", command=self.test_connection)
        self.btn_test.pack(side="left", padx=5)

        self.btn_start = tb.Button(frame_buttons, text="Iniciar Inventario", bootstyle="success", command=self.start_inventory)
        self.btn_start.pack(side="left", padx=5)

        self.btn_cancel = tb.Button(frame_buttons, text="Cancelar", bootstyle="danger", command=self.cancel_inventory, state="disabled")
        self.btn_cancel.pack(side="left", padx=5)

        # --- Consola ---
        frame_console = ttk.LabelFrame(root, text="Consola (logs)", padding=10)
        frame_console.pack(fill="both", expand=True, padx=10, pady=5)

        self.text_console = tk.Text(frame_console, wrap="word", font=console_font)
        self.text_console.pack(fill="both", expand=True, side="left")
        scrollbar = ttk.Scrollbar(frame_console, command=self.text_console.yview)
        scrollbar.pack(side="right", fill="y")
        self.text_console.config(yscrollcommand=scrollbar.set)

        # Variables de control
        self.cancel_event = threading.Event()
        self.log_file = None

    # --- Funciones ---
    def log(self, msg):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        line = f"[{timestamp}] {msg}\n"
        self.text_console.insert("end", line)
        self.text_console.see("end")
        if self.log_file:
            try:
                with open(self.log_file, "a", encoding="utf-8") as f:
                    f.write(line)
            except Exception:
                pass

    def choose_csv(self):
        file_path = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV files","*.csv")])
        if file_path:
            self.entry_csv.delete(0, tk.END)
            self.entry_csv.insert(0, file_path)

    def test_connection(self):
        host_port = self.entry_host.get().strip()
        user = self.entry_user.get().strip()
        password = self.entry_pass.get().strip()
        if not host_port or not user:
            self.log("❌ Error: Host/IP y usuario requeridos.")
            return
        hostname = f"https://{host_port}"
        try:
            resp = requests.get(f"{hostname}/graphman", auth=(user,password), verify=False, timeout=5)
            resp.raise_for_status()
            self.log("✅ Conexión correcta.")
            messagebox.showinfo("Conexión", "Conexión exitosa")
        except Exception as e:
            self.log(f"❌ Error de conexión: {e}")
            messagebox.showerror("Conexión", f"No se pudo conectar: {e}")

    def start_inventory(self):
        self.cancel_event.clear()
        self.btn_start.config(state="disabled")
        self.btn_cancel.config(state="normal")
        self.btn_test.config(state="disabled")

        default_log_name = f"GraphPy_runtime_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        self.log_file = os.path.join(os.getcwd(), default_log_name)

        thread = threading.Thread(target=self.run_inventory)
        thread.start()

    def cancel_inventory(self):
        self.cancel_event.set()
        self.log("⚠️ Petición de cancelación enviada por el usuario.")

    def run_inventory(self):
        host_port = self.entry_host.get().strip()
        user = self.entry_user.get().strip()
        password = self.entry_pass.get().strip()
        folders_input = self.entry_folders.get().strip()
        csv_name = self.entry_csv.get().strip()

        if not host_port or not user or not password or not folders_input:
            self.log("❌ Error: Campos incompletos.")
            self.reset_buttons()
            return

        hostname = f"https://{host_port}"
        auth = (user, password)

        folders_list = [("/" + f.strip()) if not f.strip().startswith("/") else f.strip() for f in folders_input.split(";") if f.strip()]

        default_prefix = "Inventario_apis_"
        filename = default_prefix + (csv_name if csv_name else datetime.now().strftime('%Y%m%d_%H%M%S')) + ".csv"
        output_csv = os.path.join(os.getcwd(), filename)

        self.log("=== Inicio Inventario APIs ===")
        start_time = time.time()
        all_services = []
        empty_folders = []

        # --- Mensaje si hay muchas carpetas ---
        if len(folders_list) > 50:
            self.log("⚠️ Atención: Gran volumen de carpetas detectado, esto puede tardar un poco. No cierre la aplicación.")

        for idx, folder in enumerate(folders_list, start=1):
            if self.cancel_event.is_set():
                break
            self.log(f"[{idx}/{len(folders_list)}] Procesando carpeta: {folder}")
            services = self.list_apis(hostname, auth, folder)
            if not services:
                self.log(f"   ⚠️ Carpeta vacía: {folder}")
                empty_folders.append(folder)
            else:
                self.log(f"   ✅ {len(services)} APIs encontradas.")
                all_services.extend(services)

        if not self.cancel_event.is_set() and all_services:
            keys = ["folderPath", "name", "resolutionPath"]
            try:
                with open(output_csv, "w", newline="", encoding="utf-8") as f:
                    writer = csv.DictWriter(f, fieldnames=keys)
                    writer.writeheader()
                    writer.writerows(all_services)
                self.log(f"Inventario guardado en: {output_csv}")
            except Exception as e:
                self.log(f"❌ Error guardando CSV: {e}")

        elapsed = time.time() - start_time
        self.log(f"Duración: {elapsed:.2f} segundos")
        self.log(f"Carpetas procesadas: {len(folders_list)}")
        self.log(f"APIs encontradas: {len(all_services)}")
        if empty_folders:
            self.log("Carpetas vacías detectadas: " + ", ".join(empty_folders))

        self.reset_buttons()

    def reset_buttons(self):
        self.btn_start.config(state="normal")
        self.btn_cancel.config(state="disabled")
        self.btn_test.config(state="normal")

    def list_apis(self, hostname, auth, folder_path):
        url = f"{hostname}/graphman"
        headers = {"Content-Type": "application/json", "X-REQUEST-TYPE": "GraphQL"}
        query = """
        query webApiServicesByFolderPath ($folderPath: String!) {
            webApiServicesByFolderPath (folderPath: $folderPath) {
                folderPath
                name
                resolutionPath
            }
        }
        """
        payload = {"query": query, "variables": {"folderPath": folder_path}}
        try:
            resp = requests.post(url, headers=headers, auth=auth, json=payload, verify=False, timeout=10)
            resp.raise_for_status()
            data = resp.json()
            return data.get("data", {}).get("webApiServicesByFolderPath", [])
        except Exception as e:
            self.log(f"❌ Error en carpeta {folder_path}: {e}")
            return []

if __name__ == "__main__":
    root = tb.Window(themename="vapor")
    app = GraphPyGUI(root)
    root.mainloop()
