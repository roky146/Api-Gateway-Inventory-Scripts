# REST & Graph API Inventory Scripts

[![Python](https://img.shields.io/badge/python-3.8%2B-blue?logo=python)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)
[![GitHub issues](https://img.shields.io/github/issues/roky146/Api-Gateway-Inventory-Scripts)](https://github.com/roky146/Api-Gateway-Inventory-Scripts/issues)
[![GitHub stars](https://img.shields.io/github/stars/roky146/Api-Gateway-Inventory-Scripts)](https://github.com/roky146/Api-Gateway-Inventory-Scripts/stargazers)
[![GitHub last commit](https://img.shields.io/github/last-commit/roky146/Api-Gateway-Inventory-Scripts)](https://github.com/roky146/Api-Gateway-Inventory-Scripts/commits/main)

---

## Descripción

Estos scripts en **Python** permiten automatizar el inventario de APIs en **7Layer API Gateway**, tanto para la versión V9 como V11.  
Permiten recorrer carpetas y subcarpetas del gateway, identificando servicios y guardando la información más relevante en **CSV** y **logs**.

---

## RESTPy (V9 y V11 si aplica)

**RESTPy** automatiza la extracción de inventario de APIs en **7Layer API Gateway V9 y V11** a través de **RESTMAN**.  

- Recorre carpetas y subcarpetas, identificando servicios.
- Guarda únicamente la ruta más profunda de cada API.
- Genera:
  - `inventario.csv` con los servicios encontrados.
  - `log.txt` con información del proceso: carpetas vacías, errores y cantidad de servicios por carpeta.
- Muestra el progreso en pantalla con colores.

**Requisitos:**
- Python 3.8 o superior.
- Dependencias:
  - `requests` (`pip install requests`)
  - `ttkbootstrap` opcional para interfaz GUI (`pip install ttkbootstrap`)

**Uso:**
1. Ejecutar el script.
2. Ingresar IP/host del gateway, credenciales y carpetas raíz.
3. El inventario y log se guardan automáticamente en la carpeta de trabajo.

---

## GraphPy (V11)

**GraphPy** permite inventariar APIs en **7Layer API Gateway V11** a través de **Graphman/GraphQL**.

- Consulta carpetas raíz específicas y obtiene todas las APIs.
- Genera:
  - `inventario.csv` con las APIs encontradas.
  - `log.txt` con detalle de procesos, carpetas vacías y errores de conexión.
- Muestra progreso en pantalla y cantidad de APIs por carpeta.

**Requisitos:**
- Python 3.8 o superior.
- Dependencias:
  - `requests` (`pip install requests`)
  - `pillow` (`pip install pillow`)
  - `ttkbootstrap` (`pip install ttkbootstrap`)

**Uso:**
1. Ejecutar el script.
2. Ingresar IP/host del gateway, credenciales y carpetas raíz.
3. El inventario y log se guardan automáticamente, facilitando la validación y comparación de servicios durante la migración de V9 a V11.

---
