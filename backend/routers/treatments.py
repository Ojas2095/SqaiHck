from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from pydantic import BaseModel
import uuid
from datetime import datetime

from ..database import get_db
from ..models import Treatment, EHRRecord, Patient

router = APIRouter(prefix="/treatments", tags=["Treatments"])

class TreatmentInput(BaseModel):
    patient_id: str

class FeedbackInput(BaseModel):
    treatment_id: str
    approved: bool
    score: float

@router.post("/")
async def get_treatment(data: TreatmentInput, db: AsyncSession = Depends(get_db)):
    try:
        # Check if patient exists
        result = await db.execute(select(Patient).filter(Patient.id == data.patient_id))
        patient = result.scalar_one_or_none()
        if not patient:
            raise HTTPException(status_code=404, detail="Patient not found")
            
        # Generate treatment mock logic (will link to ai_service later)
        treatment = Treatment(
            id=str(uuid.uuid4()),
            patient_id=data.patient_id,
            herbs="Ashwagandha, Triphala",
            diet="Warm meals",
            yoga="Surya Namaskar",
            lifestyle="Sleep early",
            confidence_score=0.85,
            ml_score=0.88,
            llm_response="AI LLM response text"
        )
        db.add(treatment)
        await db.commit()
        await db.refresh(treatment)
        
        return treatment
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/feedback")
async def submit_feedback(data: FeedbackInput, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Treatment).filter(Treatment.id == data.treatment_id))
    treatment = result.scalar_one_or_none()
    if not treatment:
        raise HTTPException(status_code=404, detail="Treatment not found")
        
    treatment.approved = data.approved
    treatment.feedback_score = data.score
    await db.commit()
    return {"status": "success"}
