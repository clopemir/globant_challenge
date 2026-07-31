# Globant Data Engineering - Challenge

## Descripción del Proyecto
Este repo contiene la solución a la prueba técnica de Data Engineering. Consiste en un ETL sencillo construido en Python que proporciona una API REST y un conjunto de procesos para la ingesta de datos históricos, almacenamiento en una BD Relacional y funciones para realizar backups y restauraciones de la información, además de poder consultar información relevante a la lógica del negocio.

## Tecnologías Utilizadas

* **Lenguaje:** Python 3
* **Despliegue:** Docker y Docker Compose
* **Arquitectura:** API REST -> (Definida en `main.py`)
* **Base de Datos y ORM:** MySQL, Definición de esquemas relacionales a través de `models.py` y `database.py`.

## Estructura del Proyecto
El proyecto sigue una estructura modular y orientada a microservicios

```text
globant_challenge/
|── app/
|    |── backup_restore.py   # Lógica para respaldar y restaurar tablas de la BD, hacia y desde un archivo `.avro`.
|    |── database.py         # Configuración, motor y sesión de la BD
|    |── initial_load.py     # Script ETL para leer los CSV's e ingestar los datos iniciales a las tablas.
|    |── main.py             # Entrypoint de la API - FastAPI
|    └── models.py           # Modelos de datos para jobs, departments y hired_employees
|── data/
|    |── departments.csv     # Datos hitóricos de departamentos
|    |── hired_employees (1).csv     # Datos hitóricos de contratacions
|    └── jobs.csv            # Datos hitóricos de trabajos
|── .env_example            # Archivo de ejemplo para configurar variables de entorno 
|── compose.yml             # Configuración de servicios Docker (App + BD)
|── Dockerfile              # Instrucciones de construcción de la imagen API
|── requirements.txt        # Dependencias del proyecto
└── README.md               # Documentación actual
```
## Setup Inicial

El entorno esta completamente Dockerizado para garantizar y facilitar el despliegue local.

### Requisitos Previos
* **Docker** instalado.
* **Docker Compose** habilitado

## Paso a Paso

1. **Clonar y acceder al directorio del proyecto:**
    ```bash
    git clone https://github.com/clopemir/globant_challenge.git
    cd globant_challenge
    ```

2. **Configurar archivo .env:**
    Copiar el archivo de ejemplo y definir las variables de entorno.
    ```bash
    cp .env_example .env
    ```

3. **Levantar Servicios:**
    Este comando construirá la imagen de la aplicación, instalará las librerías necesarias en iniciará tanto la API como la BD.
    ```bash
    docker compose up -d -o- docker compose up -d --build
    ```

4. **Acceso a la API:**
    Ahora la aplicación esta disponible en `localhost`. Para acceder al playground de FastAPI navega hacía:
    * **Swagger UI:** `http://localhost:8000/docs`
    * Desde el playground estan disponibles todos los endpoints solicitados en el challenge, incluyendo la carga histórica inicial.


## Funcionalidades Principales

1. **API REST (`main.py`):** Endpoints habilitados para ingestar la historia de los archivos CSV en la carpeta `data/` e inserción masiva a la base de datos respetando las relaciones y validando los tipos de datos. Insertar nuevos registros en lotes, cumpliendo con las reglas del reto (lotes de hasta 1000 registros).
2. **Backup y Restore (`backup_restore.py`):** 
   * **Backup:** Permite exportar el contenido de las tablas hacia el sistema de archivos s3 en formato avro.
   * **Restore:** Permite restaurar una tabla específica desde su archivo de respaldo en caso de desastre.