#!/usr/bin/env python3
# restgui_fixed_largefolders.py
"""
RestPy GUI - Inventario APIGW V9 (mejorado para carpetas grandes)
Requisitos: requests, (opcional: ttkbootstrap)
"""

import threading
import requests
import xml.etree.ElementTree as ET
import csv
import time
import os
from datetime import datetime
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from tkinter import filedialog, messagebox, font as tkfont
import tkinter as tk

try:
    import ttkbootstrap as tb
    from ttkbootstrap import ttk
    THEME = "superhero"
    USE_TTB = True
    AVAILABLE_THEMES = ["superhero", "darkly", "cyborg", "vapor", "solar", "minty", "litera", "journal", "flatly", "cosmo", "cerculean", "united", "sandstone", "pulse", "morph", "lumen"]
except Exception:
    from tkinter import ttk
    THEME = None
    USE_TTB = False
    AVAILABLE_THEMES = []

# Desactivar warnings SSL
requests.packages.urllib3.disable_warnings()

# =========================
# Lógica RestPy (core)
# =========================

hostname = ""
CANCEL_EVENT = threading.Event()

def timestamp():
    return datetime.now().strftime("%d-%m-%Y %H:%M:%S")

def fetch_with_retry(url, session, auth, retries=5, backoff_factor=1, timeout=None, log_callback=None):
    """Timeout indefinido para carpetas grandes (timeout=None)"""
    for intento in range(1, retries + 1):
        if CANCEL_EVENT.is_set():
            if log_callback:
                log_callback(f"[{timestamp()}] Cancelado antes de la petición {url}\n")
            return None
        try:
            resp = session.get(url, auth=auth, verify=False, timeout=timeout)
            resp.raise_for_status()
            return resp
        except (requests.exceptions.ReadTimeout, requests.exceptions.ConnectionError) as e:
            wait_time = backoff_factor * intento
            if log_callback:
                log_callback(f"[{timestamp()}] Timeout/conexión ({intento}/{retries}): {e}. Reintentando en {wait_time}s...\n")
            time.sleep(wait_time)
        except requests.exceptions.RequestException as e:
            if log_callback:
                log_callback(f"[{timestamp()}] Error al consultar {url}: {e}\n")
            return None
    if log_callback:
        log_callback(f"[{timestamp()}] Exhausted retries para: {url}\n")
    return None

def get_service_resolution_path(service_id, session, auth, log_callback=None):
    """Obtiene el resolutionPath de un servicio específico"""
    url = f"{hostname}/restman/1.0/services/{service_id}"
    resp = fetch_with_retry(url, session, auth, log_callback=log_callback, timeout=30, retries=3, backoff_factor=1)
    
    if resp is None:
        if log_callback:
            log_callback(f"[{timestamp()}] No se pudo obtener detalles del servicio {service_id}\n")
        return "N/A"
    
    try:
        # Parsear el XML para obtener el resolutionPath
        root = ET.fromstring(resp.text)
        ns = {"l7": "http://ns.l7tech.com/2010/04/gateway-management"}
        
        # Buscar el elemento Service y luego ServiceDetail
        service_detail = root.find(".//l7:ServiceDetail", ns)
        if service_detail is not None:
            service_mappings = service_detail.find(".//l7:ServiceMappings", ns)
            if service_mappings is not None:
                http_mapping = service_mappings.find(".//l7:HttpMapping", ns)
                if http_mapping is not None:
                    url_pattern = http_mapping.find("l7:UrlPattern", ns)
                    if url_pattern is not None and url_pattern.text:
                        return url_pattern.text
        
        # Si no encontramos el patrón de URL, intentar otra estructura
        resources = root.findall(".//l7:Resource", ns)
        for resource in resources:
            if resource.get("type") == "service":
                # Buscar dentro del contenido del recurso
                content = resource.text or ""
                if "urlPattern" in content:
                    # Extraer el urlPattern del XML interno
                    try:
                        inner_root = ET.fromstring(content)
                        url_pattern = inner_root.find(".//urlPattern")
                        if url_pattern is not None and url_pattern.text:
                            return url_pattern.text
                    except:
                        pass
        
        if log_callback:
            log_callback(f"[{timestamp()}] No se encontró resolutionPath para servicio {service_id}\n")
        return "N/A"
        
    except ET.ParseError as e:
        if log_callback:
            log_callback(f"[{timestamp()}] Error parsing XML para servicio {service_id}: {e}\n")
        return "N/A"
    except Exception as e:
        if log_callback:
            log_callback(f"[{timestamp()}] Error inesperado obteniendo resolutionPath para {service_id}: {e}\n")
        return "N/A"

def parse_services(xml_content):
    ns = {"l7": "http://ns.l7tech.com/2010/04/gateway-management"}
    root = ET.fromstring(xml_content)
    services = []
    subfolders = []
    for dep in root.findall(".//l7:Dependency", ns):
        dep_type = dep.find("l7:Type", ns).text if dep.find("l7:Type", ns) is not None else ""
        dep_name = dep.find("l7:Name", ns).text if dep.find("l7:Name", ns) is not None else ""
        dep_id = dep.find("l7:Id", ns).text if dep.find("l7:Id", ns) is not None else ""
        if dep_type == "SERVICE":
            services.append({"name": dep_name, "id": dep_id})
        elif dep_type == "FOLDER":
            subfolders.append({"name": dep_name, "id": dep_id})
    return services, subfolders

def traverse_folder(folder_id, path, session, auth, visited_folders, api_map, empty_folders, log_callback=None):
    if CANCEL_EVENT.is_set() or folder_id in visited_folders:
        return
    visited_folders.add(folder_id)

    url = f"{hostname}/restman/1.0/folders/{folder_id}/dependencies"
    resp = fetch_with_retry(url, session, auth, log_callback=log_callback, timeout=None, retries=8, backoff_factor=2)
    if resp is None:
        if log_callback:
            log_callback(f"[{timestamp()}] No se pudo obtener dependencias de carpeta {folder_id}\n")
        return

    services, subfolders = parse_services(resp.text)
    saved = 0
    for s in services:
        if s["id"] not in api_map or len(path.split("/")) > len(api_map[s["id"]]["folderPath"].split("/")):
            api_map[s["id"]] = {"serviceName": s["name"], "folderPath": path}
            saved += 1

    if log_callback:
        if saved > 0:
            log_callback(f"[{timestamp()}] Guardados {saved} servicios en {path}\n")
        elif not services and not subfolders:
            log_callback(f"[{timestamp()}] Carpeta vací­a: {path}\n")
            empty_folders.append(path)

    for idx, sf in enumerate(subfolders, start=1):
        if CANCEL_EVENT.is_set():
            return
        sub_path = f"{path}/{sf['name']}"
        if log_callback:
            log_callback(f"[{timestamp()}] Sub-progreso ({idx}/{len(subfolders)}) -> {sub_path}\n")
        traverse_folder(sf["id"], sub_path, session, auth, visited_folders, api_map, empty_folders, log_callback)

def get_all_folders(session, auth, log_callback=None):
    url = f"{hostname}/restman/1.0/folders"
    resp = fetch_with_retry(url, session, auth, log_callback=log_callback, timeout=None, retries=6, backoff_factor=2)
    if resp is None:
        if log_callback:
            log_callback(f"[{timestamp()}] No se pudo obtener la lista de carpetas.\n")
        return []
    root = ET.fromstring(resp.text)
    ns = {"l7": "http://ns.l7tech.com/2010/04/gateway-management"}
    return [(item.find("l7:Name", ns).text, item.find("l7:Id", ns).text) for item in root.findall("l7:Item", ns)]

def run_inventory(host, user, password, folders_input, output_file, log_callback):
    global hostname
    CANCEL_EVENT.clear()
    hostname = host if host.startswith("http") else "https://" + host
    target_paths = [f.strip() for f in folders_input.split(";") if f.strip()]

    session = requests.Session()
    retries = Retry(total=5, backoff_factor=1, status_forcelist=[500,502,503,504])
    session.mount("https://", HTTPAdapter(max_retries=retries))
    auth = (user, password)

    start_time = time.time()
    if log_callback:
        log_callback(f"[{timestamp()}] Obteniendo lista de carpetas raí­z...\n")
    all_folders = get_all_folders(session, auth, log_callback=log_callback)
    if log_callback:
        log_callback(f"[{timestamp()}] Se encontraron {len(all_folders)} carpetas raí­z.\n")

    # --- NUEVO: mensaje si tarda mucho en pasar al siguiente paso ---
    time_after_folders = time.time()
    if time_after_folders - start_time > 15:
        if log_callback:
            log_callback(f"[{timestamp()}] Parece que esto se va a tardar un poco, hay un gran volumen de carpetas, no cierres nada, estamos trabajando! :)\n")

    visited_folders = set()
    api_map = {}
    empty_folders = []

    # Buscar carpeta raí­z que coincida con cada target_path
    for tp in target_paths:
        matched_root = None
        for fname, fid in all_folders:
            if tp.startswith(fname):
                matched_root = (fname, fid)
                break
        if matched_root:
            traverse_folder(matched_root[1], matched_root[0], session, auth, visited_folders, api_map, empty_folders, log_callback)
        else:
            if log_callback:
                log_callback(f"[{timestamp()}] No se encontró carpeta raí­z correspondiente para: {tp}\n")

    # Obtener resolution paths
    if log_callback:
        log_callback(f"[{timestamp()}] Obteniendo resolution paths para {len(api_map)} servicios...\n")
    
    total_services = len(api_map)
    processed = 0
    
    for api_id, info in api_map.items():
        if CANCEL_EVENT.is_set():
            if log_callback:
                log_callback(f"[{timestamp()}] Proceso cancelado durante obtención de resolution paths\n")
            break
            
        processed += 1
        if log_callback and processed % 10 == 0:  # Log cada 10 servicios
            log_callback(f"[{timestamp()}] Progreso resolution paths: {processed}/{total_services}\n")
        
        resolution_path = get_service_resolution_path(api_id, session, auth, log_callback)
        info["resolutionPath"] = resolution_path

    try:
        with open(output_file, "w", newline="", encoding="utf-8") as f:
            # NUEVA columna: resolutionPath
            writer = csv.DictWriter(f, fieldnames=["folderPath", "serviceName", "serviceId", "resolutionPath"])
            writer.writeheader()

            # Guardar APIs finales en CSV
            for api_id, info in api_map.items():
                writer.writerow({
                    "folderPath": info["folderPath"], 
                    "serviceName": info["serviceName"], 
                    "serviceId": api_id,
                    "resolutionPath": info.get("resolutionPath", "N/A")
                })
    except PermissionError:
        if log_callback:
            log_callback(f"[{timestamp()}] Error: permiso denegado al escribir {output_file}\n")
        return False, None

    elapsed = time.time() - start_time
    log_file = os.path.splitext(output_file)[0] + "_log.txt"
    try:
        with open(log_file, "w", encoding="utf-8") as logf:
            logf.write(f"Inicio: {datetime.fromtimestamp(start_time).strftime('%d-%m-%Y %H:%M:%S')}\n")
            logf.write(f"Fin: {datetime.now().strftime('%d-%m-%Y %H:%M:%S')}\n")
            logf.write(f"Duración: {elapsed:.2f} segundos\n")
            logf.write(f"Archivo CSV: {output_file}\n")
            logf.write(f"Carpetas procesadas: {len(visited_folders)}\n")
            logf.write(f"APIs únicas encontradas: {len(api_map)}\n")
            logf.write("Carpetas vací­as detectadas:\n")
            for ef in empty_folders:
                logf.write(f" - {ef}\n")
    except Exception:
        pass

    if log_callback:
        log_callback(f"[{timestamp()}] Inventario completado. Guardado en {output_file}\n")
        log_callback(f"[{timestamp()}] Log guardado en {log_file}\n")

    return True, log_file

def test_connection(host, user, password, timeout=8):
    hosturl = host if host.startswith("http") else "https://" + host
    session = requests.Session()
    try:
        resp = session.get(f"{hosturl}/restman/1.0/folders", auth=(user,password), verify=False, timeout=timeout)
        resp.raise_for_status()
        return True, None
    except requests.exceptions.RequestException as e:
        return False, str(e)

# =========================
# GUI
# =========================

def get_theme_colors(theme_name):
    """Devuelve colores apropiados para el texto del banner según el tema"""
    dark_themes = ["superhero", "darkly", "cyborg", "vapor", "solar"]
    if theme_name in dark_themes:
        return "#00d4aa"  # Color verde/cian para temas oscuros
    else:
        return "#2c3e50"  # Color azul oscuro para temas claros

def build_gui():
    current_theme = {"name": THEME if USE_TTB else "default"}
    
    if USE_TTB:
        root = tb.Window(themename=current_theme["name"])
        style = tb.Style()
    else:
        root = tk.Tk()

    root.tk.call("tk", "scaling", 1.75)
    root.title("RestGUI v1.1.0 - API Gateway Inventory Tool by Marcos R.")
    root.geometry("1000x700")
    console_font = tkfont.Font(family="Consolas", size=10)

    # ASCII Art para RestGui
    ascii_art = """
    ██████╗ ███████╗███████╗████████╗ ██████╗ ██╗   ██╗██╗
    ██╔══██╗██╔════╝██╔════╝╚══██╔══╝██╔════╝ ██║   ██║██║
    ██████╔╝█████╗  ███████╗   ██║   ██║  ███╗██║   ██║██║
    ██╔══██╗██╔══╝  ╚════██║   ██║   ██║   ██║██║   ██║██║
    ██║  ██║███████╗███████║   ██║   ╚██████╔╝╚██████╔╝██║
    ╚═╝  ╚═╝╚══════╝╚══════╝   ╚═╝    ╚═════╝  ╚═════╝ ╚═╝
    """
    
    # Frame superior para el menú de temas (solo si ttkbootstrap está disponible)
    if USE_TTB:
        frame_top = ttk.Frame(root)
        frame_top.pack(fill="x", padx=8, pady=(8,0))
        
        # Spacer para empujar el combobox a la derecha
        ttk.Label(frame_top, text="").pack(side="left", expand=True)
        
        ttk.Label(frame_top, text="Tema:", font=("Segoe UI", 9)).pack(side="right", padx=(0,5))
        theme_combo = ttk.Combobox(frame_top, values=AVAILABLE_THEMES, width=12, state="readonly")
        theme_combo.set(current_theme["name"])
        theme_combo.pack(side="right", padx=(0,8))
        
        def change_theme(event=None):
            new_theme = theme_combo.get()
            if new_theme != current_theme["name"]:
                current_theme["name"] = new_theme
                try:
                    # Aplicar el tema en caliente usando el objeto style
                    style.theme_use(new_theme)
                except Exception as e:
                    messagebox.showerror("Error", f"No se pudo aplicar el tema: {e}")
                    return
                # Actualizar colores del banner/ASCII si ya existen
                text_color_local = get_theme_colors(new_theme)
                try:
                    lbl_ascii.configure(foreground=text_color_local)
                except Exception:
                    pass
                try:
                    lbl_banner.configure(foreground=text_color_local)
                except Exception:
                    pass

        theme_combo.bind("<<ComboboxSelected>>", change_theme)

    # ASCII Art
    ascii_font = tkfont.Font(family="Courier New", size=8, weight="bold")
    text_color = get_theme_colors(current_theme["name"]) if USE_TTB else "#2c3e50"
    lbl_ascii = ttk.Label(root, text=ascii_art, font=ascii_font, foreground=text_color, anchor="center")
    lbl_ascii.pack(fill="x", padx=8, pady=(8,0))

    # Banner con fuente moderna
    banner = "Programa para Inventario de APIs"
    modern_font = tkfont.Font(family="Segoe UI", size=12, weight="normal")
    lbl_banner = ttk.Label(root, text=banner, anchor="center", font=modern_font, foreground=text_color)
    lbl_banner.pack(fill="x", padx=8, pady=(0,8))

    # --- Frame configuración ---
    frame_cfg = ttk.Frame(root, padding=(8,8,8,8))
    frame_cfg.pack(fill="x", padx=8, pady=6)

    ttk.Label(frame_cfg, text="Host/IP con puerto:").grid(row=0, column=0, sticky="e", padx=4, pady=4)
    entry_host = ttk.Entry(frame_cfg, width=36)
    entry_host.grid(row=0, column=1, sticky="w", padx=4, pady=4)

    ttk.Label(frame_cfg, text="Usuario:").grid(row=1, column=0, sticky="e", padx=4, pady=4)
    entry_user = ttk.Entry(frame_cfg, width=36)
    entry_user.grid(row=1, column=1, sticky="w", padx=4, pady=4)

    ttk.Label(frame_cfg, text="Contraseña:").grid(row=2, column=0, sticky="e", padx=4, pady=4)
    entry_password = ttk.Entry(frame_cfg, show="*", width=36)
    entry_password.grid(row=2, column=1, sticky="w", padx=4, pady=4)

    ttk.Label(frame_cfg, text="Carpetas (; separadas):").grid(row=3, column=0, sticky="e", padx=4, pady=4)
    entry_folders = ttk.Entry(frame_cfg, width=36)
    entry_folders.grid(row=3, column=1, sticky="w", padx=4, pady=4)

    ttk.Label(frame_cfg, text="Archivo CSV:").grid(row=4, column=0, sticky="e", padx=4, pady=4)
    entry_output = ttk.Entry(frame_cfg, width=36)
    entry_output.grid(row=4, column=1, sticky="w", padx=4, pady=4)

    def choose_output():
        file_path = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV files","*.csv")])
        if file_path:
            entry_output.delete(0, tk.END)
            entry_output.insert(0, file_path)

    ttk.Button(frame_cfg, text="Seleccionar...", command=choose_output).grid(row=4, column=2, padx=6, pady=4)

    # --- Botones ---
    frame_actions = ttk.Frame(root)
    frame_actions.pack(fill="x", padx=8, pady=(0,8))

    btn_test = ttk.Button(frame_actions, text="Probar conexión")
    btn_start = ttk.Button(frame_actions, text="Iniciar inventario")
    btn_cancel = ttk.Button(frame_actions, text="Cancelar")
    btn_test.grid(row=0, column=0, padx=6, pady=6)
    btn_start.grid(row=0, column=1, padx=6, pady=6)
    btn_cancel.grid(row=0, column=2, padx=6, pady=6)
    btn_cancel.state(["disabled"])

    # --- Consola ---
    frame_console = ttk.LabelFrame(root, text="Consola (logs)", padding=(6,6,6,6))
    frame_console.pack(fill="both", expand=True, padx=8, pady=6)
    text_log = tk.Text(frame_console, wrap="word", font=console_font)
    text_log.pack(side="left", fill="both", expand=True)
    scrollbar = ttk.Scrollbar(frame_console, command=text_log.yview)
    scrollbar.pack(side="right", fill="y")
    text_log.config(yscrollcommand=scrollbar.set)

    current_logfile = {"path": None}

    def gui_log(msg):
        text_log.insert("end", msg)
        text_log.see("end")
        if current_logfile["path"]:
            try:
                with open(current_logfile["path"], "a", encoding="utf-8") as lf:
                    lf.write(msg)
            except Exception:
                pass

    # --- Botones ---
    def on_test():
        host = entry_host.get().strip()
        user = entry_user.get().strip()
        password = entry_password.get().strip()
        if not host or not user:
            messagebox.showwarning("Faltan datos", "Ingrese Host/IP y Usuario")
            return
        gui_log(f"[{timestamp()}] Probando conexión a {host} ...\n")
        ok, err = test_connection(host, user, password)
        if ok:
            gui_log(f"[{timestamp()}] Conexión correcta.\n")
            messagebox.showinfo("Conexión", "Conexión exitosa.")
        else:
            gui_log(f"[{timestamp()}] Fallo conexión: {err}\n")
            messagebox.showerror("Conexión", f"No se pudo conectar: {err}")

    def on_start():
        host = entry_host.get().strip()
        user = entry_user.get().strip()
        password = entry_password.get().strip()
        folders = entry_folders.get().strip()
        output_file = entry_output.get().strip()
        if not all([host, user, password, folders, output_file]):
            messagebox.showerror("Error", "Complete todos los campos")
            return

        logfile_name = os.path.splitext(output_file)[0] + "_runtime_log.txt"
        current_logfile["path"] = logfile_name
        text_log.delete("1.0", tk.END)
        gui_log(f"[{timestamp()}] Iniciando inventario...\n")

        btn_start.state(["disabled"])
        btn_test.state(["disabled"])
        btn_cancel.state(["!disabled"])
        CANCEL_EVENT.clear()

        def target():
            ok, runtime_log = run_inventory(host, user, password, folders, output_file, log_callback=gui_log)
            if ok:
                gui_log(f"[{timestamp()}] Inventario finalizado.\n")
                messagebox.showinfo("Inventario", f"Inventario guardado en:\n{output_file}")
            else:
                gui_log(f"[{timestamp()}] Inventario finalizado con errores.\n")
                messagebox.showwarning("Inventario", "Revise los logs.")
            btn_start.state(["!disabled"])
            btn_test.state(["!disabled"])
            btn_cancel.state(["disabled"])

        t = threading.Thread(target=target, daemon=True)
        t.start()

    def on_cancel():
        if messagebox.askyesno("Cancelar", "¿Desea cancelar el inventario?"):
            CANCEL_EVENT.set()
            gui_log(f"[{timestamp()}] Petición de cancelación enviada...\n")
            btn_cancel.state(["disabled"])

    btn_test.config(command=on_test)
    btn_start.config(command=on_start)
    btn_cancel.config(command=on_cancel)
    root.bind("<Escape>", lambda e=None: on_cancel() if "disabled" not in btn_cancel.state() else None)

    return root

if __name__ == "__main__":
    app = build_gui()
    app.mainloop()