# frontend/app.py
import streamlit as st
import requests

# --- Configuration ---
BACKEND_URL = "http://127.0.0.1:8000"

# --- Helper Function for API Calls ---
def verify_prescription_data(age, drugs):
    if not drugs:
        st.warning("Please enter at least one drug name.")
        return None
    
    request_data = {"age": age, "drugs": drugs}
    try:
        with st.spinner("Analyzing..."):
            response = requests.post(f"{BACKEND_URL}/verify-prescription/", json=request_data)
        if response.status_code == 200:
            return response.json()
        else:
            st.error(f"Error from backend: {response.json().get('detail', response.text)}")
            return None
    except requests.exceptions.RequestException as e:
        st.error(f"Could not connect to the backend. Please ensure it is running. Error: {e}")
        return None

# --- Main UI Layout ---
st.set_page_config(layout="wide")
st.title("💊 AI Medical Prescription Verification")
st.info("**Disclaimer:** This is an AI-powered tool for informational purposes only and is not a substitute for professional medical advice. Always consult a qualified healthcare provider.")

# --- Create Tabs for Each Feature ---
tab1, tab2, tab3 = st.tabs(["Interaction Checker", "Dosage Analyzer", "Extract from Note"])

# --- Tab 1: Interaction Checker ---
with tab1:
    st.header("Check for Harmful Drug Interactions")
    
    age_interaction = st.number_input("Patient's Age", min_value=1, max_value=120, value=30, step=1, key="age_interaction")

    if 'interaction_drugs' not in st.session_state:
        st.session_state.interaction_drugs = [{"name": "", "dosage": ""}, {"name": "", "dosage": ""}]

    for i, drug in enumerate(st.session_state.interaction_drugs):
        cols = st.columns([4, 2])
        drug['name'] = cols[0].text_input(f"Drug Name {i+1}", value=drug['name'], key=f"int_name_{i}")
        drug['dosage'] = cols[1].text_input(f"Dosage (optional) {i+1}", value=drug['dosage'], key=f"int_dosage_{i}")

    if st.button("➕ Add Another Drug", key="add_interaction_drug"):
        st.session_state.interaction_drugs.append({"name": "", "dosage": ""})
        st.rerun()

    if st.button("Analyze Interactions", type="primary"):
        valid_drugs = [d for d in st.session_state.interaction_drugs if d['name'].strip()]
        results = verify_prescription_data(age_interaction, valid_drugs)
        
        if results:
            st.subheader("🚨 Interaction Results")
            if results['interactions']:
                for interaction in results['interactions']:
                    with st.expander(f"**{interaction['drugs_involved'][0]} & {interaction['drugs_involved'][1]}** (Severity: {interaction['severity']})", expanded=True):
                        st.write(interaction['description'])
            else:
                st.success("No significant drug interactions were found.")

            st.subheader("💡 Alternative Suggestions")
            if results['alternative_suggestions']:
                for suggestion in results['alternative_suggestions']:
                    st.info(suggestion)
            else:
                st.write("No alternatives needed based on interaction analysis.")


# --- Tab 2: Dosage Analyzer ---
with tab2:
    st.header("Analyze Age-Specific Dosage Safety")
    age_dosage = st.number_input("Patient's Age", min_value=1, max_value=120, value=30, step=1, key="age_dosage")
    cols = st.columns([4, 2])
    dosage_drug_name = cols[0].text_input("Drug Name", key="dosage_drug_name")
    dosage_drug_amount = cols[1].text_input("Dosage to Analyze", placeholder="e.g., 500mg", key="dosage_drug_amount")

    if st.button("Analyze Dosage", type="primary"):
        if dosage_drug_name and dosage_drug_amount:
            drug_to_check = [{"name": dosage_drug_name, "dosage": dosage_drug_amount}]
            results = verify_prescription_data(age_dosage, drug_to_check)
            if results:
                st.subheader("🔬 Dosage Analysis Result")
                if results['dosage_warnings']:
                    st.warning(results['dosage_warnings'][0])
                else:
                    st.error("Could not get an analysis from the AI model.")
        else:
            st.warning("Please enter both a drug name and a dosage.")


# --- Tab 3: Extract from Prescription Note ---
with tab3:
    st.header("Extract Drugs from a Note")
    unstructured_text = st.text_area("Paste a prescription note here:", height=200)

    if st.button("Extract Information", type="primary"):
        if unstructured_text:
            try:
                with st.spinner("Extracting..."):
                    response = requests.post(f"{BACKEND_URL}/extract-from-text/", params={"text": unstructured_text})
                if response.status_code == 200:
                    extracted_drugs = response.json()
                    if extracted_drugs:
                        st.subheader("✅ Extracted Medication")
                        for drug in extracted_drugs:
                            st.text(f"Drug: {drug.get('name', 'N/A')}, Dosage: {drug.get('dosage', 'N/A')}")
                    else:
                        st.warning("Could not extract any structured drug information from the text.")
                else:
                    st.error(f"Error extracting text: {response.text}")
            except requests.exceptions.RequestException as e:
                st.error(f"Could not connect to the backend: {e}")
        else:
            st.warning("Please paste some text into the text area.")