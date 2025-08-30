# main.py
from fastapi import FastAPI, HTTPException
from typing import List
from models import VerificationRequest, VerificationResponse, DrugInput
from nlp_processor import extract_drug_info
from drug_api import get_interactions
from llm_handler import analyze_dosage_with_llm, suggest_alternatives_with_llm

app = FastAPI(
    title="AI Medical Prescription Verification API",
    description="An API to verify drug interactions, dosages, and suggest alternatives using online models."
)

@app.post("/extract-from-text/", response_model=List[DrugInput])
def extract_from_text(text: str):
    """Extracts structured drug information from raw text."""
    if not text.strip():
        raise HTTPException(status_code=400, detail="Text cannot be empty.")
    return extract_drug_info(text)

@app.post("/verify-prescription/", response_model=VerificationResponse)
def verify_prescription(request: VerificationRequest):
    """Verifies a prescription for interactions, dosage, and suggests alternatives."""
    drug_names = [drug.name for drug in request.drugs]

    # 1. Drug Interaction Detection
    interaction_results = get_interactions(drug_names)

    # 2. Age-Specific Dosage Recommendation (using LLM)
    dosage_warnings = []
    for drug in request.drugs:
        if drug.dosage:
            warning = analyze_dosage_with_llm(request.age, drug.name, drug.dosage)
            dosage_warnings.append(f"Analysis for {drug.name} {drug.dosage}: {warning}")

    # 3. Alternative Medication Suggestions (using LLM for interacting drugs)
    alternatives = []
    if interaction_results:
        problem_drug = interaction_results[0]['drugs_involved'][0]
        interacting_drug = interaction_results[0]['drugs_involved'][1]
        suggestion = suggest_alternatives_with_llm(problem_drug, interacting_drug)
        alternatives.append(suggestion)

    return VerificationResponse(
        interactions=interaction_results,
        dosage_warnings=dosage_warnings,
        alternative_suggestions=alternatives
    )