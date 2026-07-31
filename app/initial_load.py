import pandas as pd
import logging
from sqlalchemy.orm import Session
from pydantic import ValidationError
from database import SessionLocal, engine, Base
from models import Department, Job, HiredEmployee, DepartmentCreate, JobCreate, EmployeeCreate

# Configuración de Logging
logging.basicConfig(
    filename='../data/invalid_records.log',
    level=logging.ERROR,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

def get_valid_ids(session: Session, model) -> set:
    """Obtiene un set con todos los IDs que existen en una tabla para hacer la valdiación de llaves foraneas,"""

    records = session.query(model.id).all()

    return {record[0] for record in records}

def load_data(session: Session, csv_path:str, model_orm, model_pydantic, table_name:str, valid_deps=None, valid_jobs=None):
    
    print(f"Iniciando carga histórica de {table_name}")

    try:
        if table_name == 'departments':
            df = pd.read_csv(csv_path, names=['id', 'department'])
        elif table_name == 'jobs':
            df = pd.read_csv(csv_path, names=['id', 'job'])
        else:
            df = pd.read_csv(csv_path, names=['id', 'name', 'datetime', 'department_id', 'job_id'])

        # Reemplazo el NaN de pandas por None para identificar correctamente nulos con Pydantic
        df = df.where(pd.notnull(df), None)

        valid_records = []

        # Validar registro x registro
        for index, row in df.iterrows():
            row_dict = row.to_dict()
            try:
                # 1. Validación de schema y datatypes
                validated_data = model_pydantic(**row_dict)

                # 2. Validación de reglas de negocio, 
                if table_name == 'hired_employees':
                    if validated_data.department_id not in valid_deps:
                        raise ValidationError(f"department_id {validated_data.department_id} no existe en la tabla departments.")
                    if validated_data.job_id not in valid_jobs:
                        raise ValidationError(f"job_id {validated_data.job_id} no existe en la tabla jobs")
                
                # si pasa las validaciones se prepara para la ingesta
                valid_records.append(model_orm(**validated_data.model_dump()))
            except (ValidationError, ValueError) as e:
                # Logging de errores
                logging.error(f"Tabla: {table_name} | Fila: {index} | Datos: {row_dict} | Motivo: {e}")
    
        # Ingesta en Bloque
        if valid_records:
            session.add_all(valid_records)
            session.commit()
            print(f"Éxito: {len(valid_records)} registros ingestados en '{table_name}'.\n")
        
    except Exception as ex:
        print(f"Error critico procesando el archivo {csv_path}: {ex}")

def run_migration():
    # Validar que las tablas existan/crearlas
    Base.metadata.create_all(bind=engine)

    session = SessionLocal()

    try:
        # Carga de catálogos
        load_data(session, '../data/departments.csv', Department, DepartmentCreate, 'departments')

        load_data(session, '../data/jobs.csv', Job, JobCreate, 'jobs')

        # Ya que se han cargado las tablas base, se obtienen los ID's para validar integridad con la tabla hired_employees
        valid_departments = get_valid_ids(session, Department)
        valid_jobs = get_valid_ids(session, Job)

        # Carga de tabla transaccional
        load_data(
            session,
            '../data/hired_employees (1).csv',
            HiredEmployee,
            EmployeeCreate,
            'hired_employees',
            valid_deps=valid_departments,
            valid_jobs=valid_jobs
        )
    finally:
        session.close()
        print(f"Migración finalizada. Revisa data/invalid_records.log para ver los registros descartados.")

# if __name__ == "__main__":
#     run_migration()