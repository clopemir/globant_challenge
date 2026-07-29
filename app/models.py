from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship
from database import Base
from pydantic import BaseModel, field_validator
from datetime import datetime

# Modelos para las Tablas en función de los ejemplos de datos

class Department(Base):
    __tablename__ = "departments"
    id = Column(Integer, primary_key=True, index=True)
    department = Column(String(255), nullable=False)

class Job(Base):
    __tablename__ = "jobs"
    id = Column(Integer, primary_key=True, index=True)
    job = Column(String(255), nullable=False)

class HiredEmployee(Base):
    __tablename__ = "hired_employees"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    # La dejo como string para mantener el formato ISO original
    datetime = Column(String(255), nullable=False)
    #Llaves para los joins
    department_id = Column(Integer, ForeignKey("departments.id"), nullable=False)
    job_id = Column(Integer, ForeignKey("jobs.id"), nullable=False)
    # Relaciones para facilitar las consultas
    department = relationship("Department")
    job = relationship("Job")


# Esquemas Pydantic (Validaciones API)

class DepartmentCreate(BaseModel):
    id: int
    department: str

class JobCreate(BaseModel):
    id: int
    job: str

class EmployeeCreate(BaseModel):
    id: int
    name: str
    datetime: str
    department_id: int
    job_id: int

    @field_validator('datetime')
    def validate_iso_format(cls,v):
        try:
            # reemplazar la Z por +00:00 para pasrsear correctamente la fecha
            datetime.fromisoformat(v.replace('Z', '+00:00'))
            return v
        except ValueError:
            raise ValueError('El datetime debe estar en formato ISO')
