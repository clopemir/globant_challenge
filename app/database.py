import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
import boto3


# Conexión a MySQL
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_HOST = os.getenv("DB_HOST") 
DB_PORT = os.getenv("DB_PORT")
DB_NAME = os.getenv("DB_NAME")

SQLALCHEMY_DATABASE_URL = f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

# Creción de engine y sesión
def get_db():
    db = SessionLocal()

    try:
        yield db
    finally:
        db.close()

# Configuración de minio
minio_client = boto3.client(
    's3',
    endpoint_url = os.getenv("MINIO_ENDPOINT"),
    aws_access_key_id = os.getenv("MINIO_ACCESS_KEY"),
    aws_secret_access_key = os.getenv("MINIO_SECRET_KEY")
)