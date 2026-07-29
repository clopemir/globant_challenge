import logging
from fastapi import FastApi, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from database import engine, Base, get_db
from models import HiredEmployee, Department, Job, EmployeeCreate, DepartmentCreate, JobCreate

# Conf para el logger
logging.basicConfig(
    filename='../data/api_invalid_records.log',
    level=logging.ERROR,
    format='%(asctime)s - %(levelname)s - %(message)'
)

# Iniciar FastApi
app = FastApi(
    title="Globant Technical Test - Data Engineer - API",
    description="API para ingesta, backup y análisis de datos",
    format="1.0.0"
)

Base.metadata.create_all(bind=engine)
