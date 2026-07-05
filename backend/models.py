import uuid
from datetime import datetime
from sqlalchemy import Column, String, Integer, Float, DateTime, Boolean, Text
from .database import Base

def generate_uuid():
    return str(uuid.uuid4())

class User(Base):
    """Practitioners / Admins"""
    __tablename__ = "users"
    
    id = Column(String, primary_key=True, default=generate_uuid, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    full_name = Column(String)
    role = Column(String, default="practitioner")
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class Patient(Base):
    __tablename__ = "patients"
    
    id = Column(String, primary_key=True, default=generate_uuid, index=True)
    name = Column(String, nullable=False)
    age = Column(Integer)
    gender = Column(String)
    bmi = Column(Float)
    comorbidities_count = Column(Integer, default=0)
    outcome = Column(String)
    feature_vector = Column(Text) # Stored as JSON string
    created_at = Column(DateTime, default=datetime.utcnow)

class EHRRecord(Base):
    __tablename__ = "ehr_records"
    
    id = Column(String, primary_key=True, default=generate_uuid, index=True)
    patient_id = Column(String, index=True, nullable=False)
    visit_date = Column(DateTime, default=datetime.utcnow)
    symptoms = Column(Text)
    diagnosis = Column(String)
    prakriti = Column(String)
    comorbidities = Column(Text)
    raw_text = Column(Text)
    translated_text = Column(Text)
    language = Column(String)
    confidence_score = Column(Float, default=0.0)

class Treatment(Base):
    __tablename__ = "treatments"
    
    id = Column(String, primary_key=True, default=generate_uuid, index=True)
    patient_id = Column(String, index=True, nullable=False)
    date = Column(DateTime, default=datetime.utcnow)
    herbs = Column(Text)
    diet = Column(Text)
    yoga = Column(Text)
    lifestyle = Column(Text)
    confidence_score = Column(Float, default=0.0)
    feedback_score = Column(Float, nullable=True)
    approved = Column(Boolean, default=False)
    ml_score = Column(Float, default=0.0)
    llm_response = Column(Text)

class OutbreakAlert(Base):
    __tablename__ = "outbreak_alerts"
    
    id = Column(String, primary_key=True, default=generate_uuid, index=True)
    district = Column(String, index=True, nullable=False)
    disease = Column(String, nullable=False)
    anomaly_score = Column(Float, default=0.0)
    date_detected = Column(DateTime, default=datetime.utcnow, index=True)
    cases_reported = Column(Integer, default=0)
    severity = Column(String)
    region_cluster = Column(String)

