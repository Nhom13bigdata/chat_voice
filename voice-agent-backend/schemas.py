"""Xác định đúng dữ liệu input/output"""

from pydantic import BaseModel, Field
from typing import Optional, List


class Medication(BaseModel):
    """Thông tin thuốc"""

    name: str = Field(description="Medication name (brand or generic)")
    dose: Optional[str] = Field(None, description="Dosage (e.g., '500mg')")
    frequency: Optional[str] = Field(None, description="How often taken")
    route: Optional[str] = Field("oral", description="Administration route")
    indication: Optional[str] = Field(None, description="What it's for")
    adherence: Optional[str] = Field(None, description="Compliance status")
    effectiveness: Optional[str] = Field(None, description="How well it works")


class Allergy(BaseModel):
    """Thông tin dị ứng"""

    allergen: str = Field(description="What causes allergy")
    reaction: Optional[str] = Field(None, description="Symptoms/reactions")
    severity: str = Field(description="mild,  moderate, serious, or life-threatening")
    requires_intervention: bool = Field(False, description="Needs EpiPen/ER")

class ChiefComplaint(BaseModel):
    """Thông tin triệu chứng chính"""
    complaint: str = Field(description="Main symptom/issue")
    onset: Optional[str] = Field(None, description="sudden or gradual")
    duration: Optional[str] = Field(None, description="How long")
    severity: str = Field(description="Severity rating")
    Location: Optional[str] = Field(None, description="Body location")

class PatientInfo(BaseModel):
    """Thông tin bệnh nhân"""
    name: Optional[str] = Field(None, description="Patient name")
    date_of_birth: Optional[str] = Field(None, description="Date of birth")
    gender: Optional[str] = Field(None, description="Patient gender")
    phone: Optional[str] = Field(None, description="Patient phone number")
    email: Optional[str] = Field(None, description="Patient email address")
    address: Optional[str] = Field(None, description="Patient address")

class PresentIllness(BaseModel):
    """Current illness details"""
    chief_complaints: List[ChiefComplaint] = []
    symptoms: List[str] = []
    timeline: Optional[str] = None


class PastMedicalHistory(BaseModel):
    """Past medical conditions"""
    conditions: List[str] = []
    surgeries: List[str] = []
    hospitalizations: List[str] = []


class FamilyHistory(BaseModel):
    """Family medical history"""
    conditions: List[str] = []


class SocialHistory(BaseModel):
    """Social and lifestyle factors"""
    smoking: Optional[str] = None
    alcohol: Optional[str] = None
    drugs: Optional[str] = None
    occupation: Optional[str] = None
    exercise: Optional[str] = None


class MedicalIntake(BaseModel):
    """Complete medical intake data"""
    patient_info: Optional[PatientInfo] = None
    present_illness: Optional[PresentIllness] = None
    medications: List[Medication] = []
    allergies: List[Allergy] = []
    past_medical_history: Optional[PastMedicalHistory] = None
    family_history: Optional[FamilyHistory] = None
    social_history: Optional[SocialHistory] = None