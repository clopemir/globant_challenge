import os
import io
import pandas as pd
import fastavro
from fastapi import HTTPException
from sqlalchemy import text, inspect
from database import engine, minio_client
from dotenv import load_dotenv
from datetime import datetime, timezone

load_dotenv()

# Definición del Bucket en minio/s3
BUCKET_NAME = os.getenv("MINIO_BUCKET_BACKUPS")

# Schemas para fastavro
AVRO_SCHEMAS = {
    "departments" : {
        "type" : "record",
        "name" : "Department",
        "fields" : [
            {
                "name" : "id",
                "type" : "int"
            },
            {
                "name" : "department",
                "type" : "string"
            }
        ]
    },
    "jobs" : {
        "type" : "record",
        "name" : "Jobs",
        "fields" : [
            {
                "name" : "id",
                "type" : "int"
            },
            {
                "name" : "job",
                "type" : "string"
            }
        ]
    },
    "hired_employees" : {
        "type" : "record",
        "name" : "HiredEmployee",
        "fields" : [
            {
                "name" : "id",
                "type" : "int"
            },
            {
                "name" : "name",
                "type" : "string"
            },
            {
                "name" : "datetime",
                "type" : "string"
            },
            {
                "name" : "department_id",
                "type" : "int"
            },
            {
                "name" : "job_id",
                "type" : "int"
            }
        ]
    }
}

# Validar que el bucket exista y si no crearlo
def bucket_exists():

    try:
        minio_client.head_bucket(Bucket=BUCKET_NAME)
    except Exception:
        minio_client.create_bucket(Bucket=BUCKET_NAME)

# Función para crear el Backup
def create_backup(table_name: str):

    if table_name not in AVRO_SCHEMAS:
        raise ValueError(f"La tabla: {table_name} no se puede respaldar")
    
    bucket_exists()

    # Lectura de los datos en MySQL con Pandas
    query = f"SELECT * from {table_name}"
    df = pd.read_sql(query, engine)

    # Parsear a diccionario según los esquemas admitidos por fastavro
    records = df.to_dict(orient="records")

    # Persistimos en memoria
    avro_buffer = io.BytesIO()
    fastavro.writer(avro_buffer, AVRO_SCHEMAS[table_name], records)
    avro_buffer.seek(0)

    # Subimos el fichero .avro a minio
    file_name = f"{table_name}_backup.avro"
    minio_client.put_object(
        Bucket = BUCKET_NAME,
        Key = file_name,
        Body = avro_buffer.getvalue()
    )

    return {
        "message" : f"Backup creado correctamente",
        "file" : file_name,
        "records_backed_up" : len(records)
    }

# Función para restaurar una tabla a partir del backup en avro
def restore_data(table_name: str):
    if table_name not in AVRO_SCHEMAS:
        raise ValueError(f"La tabla: {table_name} no se puede restaurar.")
    
    file_name = f"{table_name}_backup.avro"

    try:
        # Obtenemos el fichero avro desde minio
        response = minio_client.get_object(
            Bucket = BUCKET_NAME,
            Key = file_name
        )
        avro_buffer = io.BytesIO(response["Body"].read())

        # Leemos el backup
        reader = fastavro.reader(avro_buffer)
        records = [record for record in reader]

        if not records:
            return {
                "message" : "El backup no tiene datos para procesar, no se realizará ninguna acción."
            }
        
        # Creamos el dataset para ingestarlo en MySQL
        df = pd.DataFrame(records)

        # Para la función de restaurar, truncamos la tabla actual y cargamos todo lo del respaldo.
        with engine.begin() as conn:
            # FIX: Validar que la tabla existe antes de restaurar
            inspector = inspect(conn)
            table_exists = inspector.has_table(table_name)
            # Desactivar temporalmente la revisión de FK's, para evitar errores de restricción
            conn.execute(text("SET FOREIGN_KEY_CHECKS = 0;"))

            if table_exists:

                conn.execute(text(f"TRUNCATE TABLE {table_name};"))
                df.to_sql(name=table_name, con=conn, if_exists='append', index=False)
            else:
                df.to_sql(name=table_name, con=conn, if_exists='replace', index=False)
                
            # Activo nuevamente la revisión de FK's
            conn.execute(text("SET FOREIGN_KEY_CHECKS = 1;"))

        return {
            "message": f"Restauración correcta." if table_exists else "Tabla recreada y restaurada correctamente.",
            "table" : table_name,
            "records_restored" : len(records)
        }
    except minio_client.exceptions.NoSuchKey:
        raise FileNotFoundError(f"No se encontró el archivo de backup: {file_name} en MinIO")