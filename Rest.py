import requests
import xml.etree.ElementTree as ET
import csv
import getpass
import time
from datetime import datetime
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import re
import os

# Desactivar warnings de certificado
requests.packages.urllib3.disable_warnings()

# Colores ANSI
WHITE = "\033[97m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
RESET = "\033[0m"

# ASCII con color
ASCII_ART = rf"""
{GREEN}
__________                 __ __________        
\______   \ ____   _______/  |\______   \___.__.
 |       _// __ \ /  ___/\   __\     ___<   |  |
 |    |   \  ___/ \___ \  |  | |    |    \___  |
 |____|_  /\___  >____  > |__| |____|    / ____|
        \/     \/     \/                 \/     
RestPy By Marcos R.  {RESET}
"""

def timestamp():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def fetch_with_retry(url, session, auth, retries=5, backoff_factor=5):
    for intento in range(1, retries + 1):
        try:
            resp = session.get(url, auth=auth, verify=False, timeout=None)
            resp.raise_for_status()
            return resp
        except requests.exceptions.RequestException as e:
            wait_time = backoff_factor * intento
            print(f"{YELLOW}[{timestamp()}] Error/conexión ({intento}/{retries}): {e}. Reintentando en {wait_time}s...{RESET}")
            time.sleep(wait_time)
    return None

def parse_services(xml_content):
    """Extrae servicios y subcarpetas de la respuesta XML"""
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

def traverse_folder(folder_id, path, session, auth, visited_folders, api_map, empty_folders):
    """Recorre carpeta y subcarpetas, guardando solo la ruta más profunda de cada API"""
    if folder_id in visited_folders:
        return
    visited_folders.add(folder_id)

    url = f"{hostname}/restman/1.0/folders/{folder_id}/dependencies"
    resp = fetch_with_retry(url, session, auth)
    if resp is None:
        print(f"{RED}[{timestamp()}] No se pudo obtener carpeta {folder_id}{RESET}")
        return

    services, subfolders = parse_services(resp.text)

    count_saved = 0
    # Guardar servicios en el mapa, reemplazando la ruta si es más profunda
    for s in services:
        if s["id"] not in api_map or len(path.split("/")) > len(api_map[s["id"]]["folderPath"].split("/")):
            api_map[s["id"]] = {"serviceName": s["name"], "folderPath": path}
            count_saved += 1

    # Mostrar cantidad guardada por carpeta
    if count_saved > 0:
        print(f"{GREEN}[{timestamp()}] Guardados {count_saved} servicios en {path}{RESET}")
    elif not services and not subfolders:
        print(f"{YELLOW}[{timestamp()}] Carpeta vacía: {path}{RESET}")
        empty_folders.append(path)

    # Procesar subcarpetas
    for idx, sf in enumerate(subfolders, start=1):
        sub_path = f"{path}/{sf['name']}"
        print(f"{WHITE}[{timestamp()}] Procesando subcarpeta ({idx}/{len(subfolders)}): {sub_path}{RESET}")
        traverse_folder(sf["id"], sub_path, session, auth, visited_folders, api_map, empty_folders)

def get_all_folders(session, auth):
    url = f"{hostname}/restman/1.0/folders"
    resp = fetch_with_retry(url, session, auth)
    if resp is None:
        print(f"{RED}[{timestamp()}] No se pudo obtener la lista de carpetas.{RESET}")
        return []
    ns = {"l7": "http://ns.l7tech.com/2010/04/gateway-management"}
    root = ET.fromstring(resp.text)
    return [(item.find("l7:Name", ns).text, item.find("l7:Id", ns).text) for item in root.findall("l7:Item", ns)]

def main():
    global hostname
    print(ASCII_ART)

    hostname_input = input(f"{WHITE}Ingrese IP o host con puerto (ej: 192.168.242.20:8443): {RESET}").strip()
    hostname = hostname_input if hostname_input.startswith("http") else "https://" + hostname_input
    user = input(f"{WHITE}Usuario: {RESET}").strip()
    password = getpass.getpass(f"{WHITE}Contraseña: {RESET}")
    folders_input = input(f"{WHITE}Carpetas raíz (separadas por punto y coma, ej: BHDL;BHDIB): {RESET}").strip()
    target_folders = [f.strip() for f in folders_input.split(";") if f.strip()]

    safe_ip = re.sub(r'[<>:"/\\|?*]', '_', hostname_input)
    default_name = f"Inventario_apis_{safe_ip}.csv"
    output_file = input(f"{WHITE}Nombre CSV (ENTER para usar '{default_name}'): {RESET}").strip()
    if not output_file:
        output_file = default_name
    log_file = os.path.splitext(output_file)[0] + "_log.txt"

    session = requests.Session()
    retries = Retry(total=5, backoff_factor=1, status_forcelist=[500,502,503,504])
    session.mount("https://", HTTPAdapter(max_retries=retries))
    auth = (user, password)

    start_time = time.time()
    print(f"\n{WHITE}[{timestamp()}] Obteniendo lista de carpetas...{RESET}")
    all_folders = get_all_folders(session, auth)
    print(f"{GREEN}[{timestamp()}] Se encontraron {len(all_folders)} carpetas.{RESET}")

    visited_folders = set()
    api_map = {}
    empty_folders = []

    with open(output_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["folderPath", "serviceName", "serviceId"])
        writer.writeheader()

        target_folders_info = [(name, fid) for name, fid in all_folders if any(name.startswith(tf) for tf in target_folders)]
        for idx, (fname, fid) in enumerate(target_folders_info, start=1):
            print(f"{WHITE}[{timestamp()}] [{idx}/{len(target_folders_info)}] Procesando carpeta: {fname}{RESET}")
            traverse_folder(fid, fname, session, auth, visited_folders, api_map, empty_folders)

        # Guardar APIs finales en CSV
        for api_id, info in api_map.items():
            writer.writerow({"folderPath": info["folderPath"], "serviceName": info["serviceName"], "serviceId": api_id})

    elapsed = time.time() - start_time
    # Guardar log
    with open(log_file, "w", encoding="utf-8") as log:
        log.write(f"Inicio: {datetime.fromtimestamp(start_time).strftime('%Y-%m-%d %H:%M:%S')}\n")
        log.write(f"Fin: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        log.write(f"Duración: {elapsed:.2f} segundos\n")
        log.write(f"Archivo CSV: {output_file}\n")
        log.write(f"Carpetas procesadas: {len(visited_folders)}\n")
        log.write(f"APIs únicas encontradas: {len(api_map)}\n")
        log.write(f"Carpetas vacías detectadas:\n")
        for ef in empty_folders:
            log.write(f" - {ef}\n")

    print(f"\n{GREEN}[{timestamp()}] Inventario completado. Guardado en {output_file}{RESET}")
    print(f"{WHITE}Log guardado en {log_file}{RESET}")

if __name__ == "__main__":
    main()
