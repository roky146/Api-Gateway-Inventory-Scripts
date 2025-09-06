import requests
import json
import sys
import csv
import os
from datetime import datetime
import urllib3
import re
import time

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Colores ANSI
WHITE = "\033[97m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
RESET = "\033[0m"

ASCII_ART = rf"""
{GREEN}
  ________                    .__   __________        
 /  _____/___________  ______ |  |__\______   \___.__.
/   \  __\_  __ \__  \ \____ \|  |  \|     ___<   |  |
\    \_\  \  | \// __ \|  |_> >   Y  \    |    \___  |
 \______  /__|  (____  /   __/|___|  /____|    / ____|
        \/           \/|__|        \/          \/     
                                                         
GraphPy by Marcos R.
{RESET}
"""

print(ASCII_ART)

# --- Entrada de usuario ---
host_port = input("Ingrese IP o host con puerto (ej: 10.112.0.89:8443): ").strip()
user = input("Usuario: ").strip()
password = input("Contraseña: ").strip()
folders_input = input("Carpetas raíz para inventario (separadas por punto y coma, ej: BHDL;/BHDIB/): ").strip()

# Separar y limpiar carpetas, agregando / si falta
folders_list = []
for f in folders_input.split(";"):
    f = f.strip()
    if not f:
        continue
    if not f.startswith("/"):
        f = "/" + f
    folders_list.append(f)

auth = (user, password)
hostname = f"https://{host_port}"

# Log
log_file = os.path.join(os.getcwd(), f"GraphPy_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt")

def log(msg):
    with open(log_file, "a", encoding="utf-8") as logf:
        logf.write(msg + "\n")

# --- Función para llamar Graphman ---
def list_apis(folder_path):
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
        response = requests.post(url, headers=headers, auth=auth, json=payload, verify=False, timeout=10)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"{RED}Error de conexión: {e}{RESET}")
        log(f"[ERROR] {datetime.now()} - Error de conexión en carpeta {folder_path}: {e}")
        return []

    try:
        data = response.json()
    except json.JSONDecodeError:
        print(f"{RED}Error: respuesta no es JSON válido{RESET}")
        log(f"[ERROR] {datetime.now()} - Respuesta no JSON en carpeta {folder_path}")
        return []

    services = data.get("data", {}).get("webApiServicesByFolderPath", [])
    return services

def main():
    start_time = time.time()
    all_services = []
    empty_folders = []

    print(f"\n{WHITE}Iniciando inventario...{RESET}")
    log(f"=== Inicio inventario {datetime.now()} ===")

    for idx, folder in enumerate(folders_list, start=1):
        print(f"\n[{idx}/{len(folders_list)}] Procesando carpeta: {folder}")
        services = list_apis(folder)
        if not services:
            print(f"{YELLOW}   No se encontraron APIs en esta carpeta.{RESET}")
            empty_folders.append(folder)
            log(f"[INFO] {datetime.now()} - Carpeta vacía: {folder}")
        else:
            print(f"{GREEN}   Se encontraron {len(services)} APIs.{RESET}")
            all_services.extend(services)
            log(f"[INFO] {datetime.now()} - {len(services)} APIs en carpeta {folder}")

    if not all_services:
        print(f"\n{YELLOW}No se encontraron APIs en ninguna de las carpetas proporcionadas.{RESET}")
        log(f"[INFO] {datetime.now()} - No se encontraron APIs en ninguna carpeta.")
        return

    default_prefix = "Inventario_apis_ambiente_"
    user_input = input(f"\nIngrese el nombre del archivo CSV (prefijo '{default_prefix}' ya incluido): ").strip()
    if not user_input:
        filename = default_prefix + datetime.now().strftime('%Y%m%d_%H%M%S') + ".csv"
    else:
        filename = default_prefix + user_input + ".csv"

    output_csv = os.path.join(os.getcwd(), filename)
    keys = ["folderPath", "name", "resolutionPath"]

    try:
        with open(output_csv, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=keys)
            writer.writeheader()
            writer.writerows(all_services)
    except PermissionError:
        print(f"{RED}No se pudo guardar el CSV. Cierre cualquier archivo abierto y verifique permisos: {output_csv}{RESET}")
        log(f"[ERROR] {datetime.now()} - No se pudo guardar CSV {output_csv}")
        return

    elapsed = time.time() - start_time
    print(f"\n{GREEN}Inventario guardado correctamente en: {output_csv}{RESET}")
    print(f"{WHITE}Log guardado en {log_file}{RESET}")
    log(f"=== Fin inventario {datetime.now()} ===")
    log(f"Duración: {elapsed:.2f} segundos")
    log(f"APIs totales encontradas: {len(all_services)}")
    if empty_folders:
        log(f"Carpetas vacías: {', '.join(empty_folders)}")

if __name__ == "__main__":
    while True:
        print("\n=== Inventario de APIs PPD V11 (GraphPy) ===")
        print("1 - Ejecutar inventario")
        print("0 - Salir")
        choice = input("Seleccione una opción: ").strip()
        if choice == "1":
            main()
            input("\nPresione ENTER para regresar al menú...")
        elif choice == "0":
            print("Saliendo del programa.")
            break
        else:
            print("Opción no válida. Intente nuevamente.\n")
