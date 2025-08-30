# models.py
from pydantic import BaseModel
from typing import List, Optional

class DrugInput(BaseModel):
    name: str
    dosage: Optional[str] = None

class VerificationRequest(BaseModel):
    age: int
    drugs: List[DrugInput]

class InteractionResult(BaseModel):
    drugs_involved: List[str]
    severity: str
    description: str

class VerificationResponse(BaseModel):
    interactions: List[InteractionResult]
    dosage_warnings: List[str]
    alternative_suggestions: List[str]