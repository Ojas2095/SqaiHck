from fastapi import APIRouter, Depends, HTTPException, File, UploadFile, Form
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from pydantic import BaseModel
import random
import uuid
import tempfile
import os

from ..database import get_db
from ..models import EHRRecord

router = APIRouter(prefix="/ehr", tags=["EHR"])

class EHRInput(BaseModel):
    patient_id: Optional[str] = None
    voice_text: str
    language: str

@router.post("/")
async def create_ehr(data: EHRInput, db: AsyncSession = Depends(get_db)):
    try:
        from ..services import voice_creator
        
        patient_id = data.patient_id or f"PAT-{random.randint(100, 999):04d}"
        
        # AI ML generation
        ai_record = voice_creator.create_ehr(patient_id, data.voice_text, data.language)
        
        # SQLAlchemy Persistence
        new_record = EHRRecord(
            id=ai_record["id"],
            patient_id=ai_record["patient_id"],
            symptoms=ai_record["symptoms"],
            diagnosis=ai_record["diagnosis"],
            prakriti=ai_record["prakriti"],
            raw_text=ai_record["raw_text"],
            translated_text=ai_record["translated_text"],
            language=ai_record["language"]
        )
        db.add(new_record)
        await db.commit()
        await db.refresh(new_record)
        return new_record
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/transcribe")
async def transcribe_audio(audio: UploadFile = File(None), language: str = Form("en")):
    if not audio:
        raise HTTPException(status_code=400, detail="No audio file")
    
    # Placeholder for faster-whisper logic
    return {"text": "This is a transcribed text stub.", "language": language}
