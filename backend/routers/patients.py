from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from pydantic import BaseModel
from typing import List, Optional
import uuid

from ..database import get_db
from ..models import Patient

router = APIRouter(prefix="/patients", tags=["Patients"])

class PatientCreate(BaseModel):
    name: str
    age: int
    gender: str
    bmi: Optional[float] = None
    comorbidities_count: int = 0

@router.post("/", response_model=dict)
async def create_patient(patient: PatientCreate, db: AsyncSession = Depends(get_db)):
    db_patient = Patient(
        id=str(uuid.uuid4()),
        name=patient.name,
        age=patient.age,
        gender=patient.gender,
        bmi=patient.bmi,
        comorbidities_count=patient.comorbidities_count
    )
    db.add(db_patient)
    await db.commit()
    await db.refresh(db_patient)
    return {"status": "success", "patient_id": db_patient.id}

@router.get("/{patient_id}")
async def get_patient(patient_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Patient).filter(Patient.id == patient_id))
    patient = result.scalar_one_or_none()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    return patient
