# RESTPy

RESTPy es un script en Python diseñado para automatizar el inventario de APIs en **7Layer API Gateway V9** utilizando la interfaz **RESTMAN**.  
Recorre carpetas y subcarpetas del gateway, identificando servicios y guardando únicamente la ruta más profunda de cada API. Genera un archivo **CSV** con el inventario y un **log** con información del proceso, incluyendo carpetas vacías, errores de conexión y cantidad de servicios encontrados por carpeta.

Para utilizarlo, se necesita **Python 3.8 o superior** y tener instalada la dependencia **requests** (`pip install requests`). Ejecutar el script, ingresar IP/host del gateway, credenciales y carpetas raíz a inventariar. El script mostrará progreso en pantalla con colores y guardará el inventario y el log en la carpeta de trabajo.

# GraphPy

GraphPy es un script en Python para inventariar APIs en **7Layer API Gateway V11** a través de la interfaz **Graphman/GraphQL**.  
Permite consultar carpetas raíz específicas, obtener todas las APIs contenidas y generar un **CSV** con el inventario, así como un **log** detallado del proceso. Muestra en pantalla el progreso, cantidad de APIs encontradas por carpeta y notifica carpetas vacías o errores de conexión.

Para utilizarlo, se necesita **Python 3.8 o superior** y tener instalada la dependencia **requests** (`pip install requests`). Ejecutar el script, ingresar IP/host del gateway, credenciales y carpetas raíz a inventariar. El inventario y el log se guardan automáticamente en la carpeta de trabajo, facilitando la validación y comparación de servicios durante la migración de V9 a V11.
