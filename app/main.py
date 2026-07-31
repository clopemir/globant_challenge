import logging
import traceback
from fastapi import FastAPI, Depends, HTTPException, status, Path
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.orm import Session
from typing import List
from database import Base, get_db, engine
from initial_load import run_migration
from models import HiredEmployee, Department, Job, ApiEmployeeCreate, ApiDepartmentCreate, ApiJobCreate
from backup_restore import create_backup, restore_data

# Conf para el logger
logging.basicConfig(
    filename='../data/api_invalid_records.log',
    level=logging.ERROR,
    format='%(asctime)s - %(levelname)s - %(message)'
)

# Iniciar FastApi
app = FastAPI(
    title="Globant Technical Test - Data Engineer - API",
    description="API para ingesta, backup y análisis de datos",
    format="1.0.0"
)

# Asegurar que las tablas existan en la BD
Base.metadata.create_all(bind=engine)

# Endpoint para recarga histórica
@app.post("/api/historical/batch", status_code=status.HTTP_201_CREATED)
def ingest_historical_batch():
    try:
        run_migration()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error en recarga de historia: {str(e)}")
    
    return {
        "message" : "Historia procesada",
        "note" : "Revisar el archivo de logs para el detalle de los rechazados"
    }
    

# Endpoints para carga ETL
@app.post("/api/employees/batch", status_code=status.HTTP_201_CREATED)
def ingest_employees_batch(
    employees: List[ApiEmployeeCreate],
    db: Session = Depends(get_db)
):
    """
    Recibe el lote de registros Inserta los válidos y descarta e informa en log los inválidos
    
    :param employees: Lote de empleados para ingestar.
    :type employees: List[ApiEmployeeCreate]
    :param db: Conexión a la base de datos
    :type db: Session
    """
    if not (1 <= len(employees) <= 1000):
        raise HTTPException(
            status_code=400,
            detail="El tamaño del lote debe estar entre 1 y 1000  registros"
        )
    # Cargo los ID's de departamentos y trabajos en memoria
    valid_deps = {dept[0] for dept in db.query(Department.id).all()}
    valid_jobs = {job[0] for job in db.query(Job.id).all()}

    valid_records = []
    invalid_count = 0

    # Procesamiento del lote
    for emp in employees:

        if emp.department_id not in valid_deps:
            logging.error(f"Registro {emp.id} rechazado: el department_id - {emp.department_id} no existe.")
            invalid_count += 1
            continue
        if emp.job_id not in valid_jobs:
            logging.error(f"Registro {emp.id} rechazado: el job_id - {emp.job_id} no existe.")
            invalid_count += 1
            continue

        valid_records.append(HiredEmployee(**emp.model_dump()))

    if valid_records:
        try:
            db.add_all(valid_records)
            db.commit()
        except Exception as e:
            db.rollback()
            raise HTTPException(status_code=500, detail=f"Error en BD: {str(e)}")
    
    return {
        "message" : "Lote procesado",
        "total_received" : len(employees),
        "inserted" : len(valid_records),
        "rejected" : invalid_count,
        "note" : "Revisar el archivo de logs para el detalle de los rechazados" if invalid_count > 0 else "Todos los registros OK"
    }

@app.post("/api/departments/batch", status_code=status.HTTP_201_CREATED)
def ingest_departments_batch(
    departments: List[ApiDepartmentCreate],
    db: Session = Depends(get_db)
):
    """
    Recibe el lote de registros Inserta los válidos y descarta e informa en log los inválidos
    
    :param departments: Lote de departamentos para ingestar.
    :type departments: List[ApiDepartmentCreate]
    :param db: Conexión a la base de datos
    :type db: Session
    """
    if not (1 <= len(departments) <= 1000):
        raise HTTPException(
            status_code=400,
            detail="El tamaño del lote debe estar entre 1 y 1000  registros"
        )

    valid_records = []
    invalid_count = 0

    # Procesamiento del lote
    for dep in departments:

        if dep.department == '':
            logging.error(f"Registro {dep.department} rechazado: el nombre es obligatorio.")
            invalid_count += 1
            continue

        valid_records.append(Department(**dep.model_dump()))

    if valid_records:
        try:
            db.add_all(valid_records)
            db.commit()
        except Exception as e:
            db.rollback()
            raise HTTPException(status_code=500, detail=f"Error en BD: {str(e)}")
    
    return {
        "message" : "Lote procesado",
        "total_received" : len(departments),
        "inserted" : len(valid_records),
        "rejected" : invalid_count,
        "note" : "Revisar el archivo de logs para el detalle de los rechazados" if invalid_count > 0 else "Todos los registros OK"
    }

@app.post("/api/jobs/batch", status_code=status.HTTP_201_CREATED)
def ingest_jobs_batch(
        jobs: List[ApiJobCreate],
        db: Session = Depends(get_db)
):
    """
    Recibe el lote de registros Inserta los válidos y descarta e informa en log los inválidos
    
    :param jobs: Lote de Jobs para ingestar.
    :type jobs: List[ApiJobCreate]
    :param db: Conexión a la base de datos
    :type db: Session
    """
    if not (1 <= len(jobs) <= 1000):
        raise HTTPException(
            status_code=400,
            detail="El tamaño del lote debe estar entre 1 y 1000 registros"
        )
    
    valid_records = []
    invalid_count = 0

    for job in jobs:

        if job.job == '':
            logging.error(f"Registro {job.job} rechazado: el nombre es obligatorio.")
            invalid_count += 1
            continue

        valid_records.append(Job(**job.model_dump()))

    if valid_records:
        try:
            db.add_all(valid_records)
            db.commit()
        except Exception as e:
            db.rollback()
            raise HTTPException(status_code=500, detail=f"Error en BD: {str(e)}")
    
    return {
        "message" : "Lote procesado",
        "total_received" : len(jobs),
        "inserted" : len(valid_records),
        "rejected" : invalid_count,
        "note" : "Revisar el archivo de logs para el detalle de los rechazados" if invalid_count > 0 else "Todos los registros OK"
    }

#Endpoints para backup y restore
@app.post("/api/backup/{table_name}")
def backup_table(
    table_name: str = Path(..., description="Nombre de la tabla (hired_employees, jobs, departments)")
):
    try:
        result = create_backup(table_name)
        print(result)
        return result
    except ValueError as e:
        traceback.print_exc()
        raise HTTPException(
            status_code=400,
            detail=str(e)
        )
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )
    
@app.post("/api/restore/{table_name}")
def restore_table(
    table_name: str = Path(..., description="Nombre de la tabla (hired_employees, jobs, departments)")
):
    try:
        result = restore_data(table_name)
        print(result)
        return result
    except ValueError as e:
        traceback.print_exc()
        raise HTTPException(
            status_code=400,
            detail=str(e)
        )
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )

# Endpoints de consulta SQL/Análisis
@app.post("/api/metrics/hired-by-q")
def get_hired_by_q(db: Session = Depends(get_db)):
    """
    Devuelve el numero de empleados contratados por departamento y trabajo en 2021
    agrupados por trimestre y ordenados alfabéticamente
    """

    query = text("""
            SELECT
                d.department,
                j.job,
                SUM(CASE WHEN QUARTER(he.datetime) = 1 THEN 1 ELSE 0 END) AS Q1,
                SUM(CASE WHEN QUARTER(he.datetime) = 2 THEN 1 ELSE 0 END) AS Q2,
                SUM(CASE WHEN QUARTER(he.datetime) = 3 THEN 1 ELSE 0 END) AS Q3,
                SUM(CASE WHEN QUARTER(he.datetime) = 4 THEN 1 ELSE 0 END) AS Q4
            FROM hired_employees he
            JOIN departments d
                ON he.department_id = d.id
            JOIN jobs j
                ON he.job_id = j.id
            WHERE YEAR(he.datetime) = 2021
            GROUP BY
                d.department,
                j.job
            ORDER BY
                d.department ASC,
                j.job ASC;
        """)

    try:
        result = db.execute(query).mappings().all()

        return [dict(row) for row in result]
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            details=str(e)
        )
    
@app.post("/api/metrics/deps-over-avg")
def get_deps_over_avg(db: Session = Depends(get_db)):
    """
    Devuelve el los departamentos con contrataciones mayores al promedio general en 2021, ordenado campo hired DESC.
    """

    query = text("""
            SELECT
                d.id,
                d.department,
                COUNT(*) AS hired
            FROM hired_employees he
            JOIN departments d
            ON he.department_id = d.id
            WHERE YEAR(he.datetime) = 2021
            GROUP BY
                d.id,
                d.department
            HAVING COUNT(*) > (
                SELECT AVG(department_hires)
                FROM (
                    SELECT COUNT(*) as department_hires
                    FROM hired_employees
                    WHERE YEAR(datetime) = 2021
                    GROUP BY department_id
                ) AS dept_counts
            )
            ORDER BY hired DESC;
        """)

    try:
        result = db.execute(query).mappings().all()

        return [dict(row) for row in result]
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            details=str(e)
        )