import requests
from typing import Optional, List

BASE_URL = "https://rxnav.nlm.nih.gov/REST"

def _find_best_rxcui_from_candidates(candidates: list, drug_name: str) -> Optional[str]:
    """Helper function to parse a list of candidates and find the best RxCUI."""
    if not candidates:
        return None

    # This list is ordered by priority. "IN" (Ingredient) is the most desired TTY.
    priority_ttys = ["IN", "SCD", "BN", "SBD"]
    best_candidate = None
    best_priority = len(priority_ttys)

    for candidate in candidates:
        tty = candidate.get("tty")
        if tty in priority_ttys:
            current_priority = priority_ttys.index(tty)
            if current_priority < best_priority:
                best_candidate = candidate
                best_priority = current_priority
                if best_priority == 0:
                    break

    if not best_candidate:
        best_candidate = candidates[0]

    rxcui = best_candidate.get("rxcui")
    if rxcui:
        print(f"  -> Found Best Match RxCUI: {rxcui} (TTY: {best_candidate.get('tty')}) for '{drug_name}'")
        return rxcui
    
    return None

def get_rxcui(drug_name: str, depth=0) -> Optional[str]:
    """
    Gets the RxNorm Concept Unique Identifier (RxCUI) using an even more resilient, multi-step search.
    """
    if depth > 2: # Prevents infinite recursion
        return None
        
    print(f"--- Starting FINAL resilient search for drug: '{drug_name}' ---")
    
    # --- Step 1: Use the 'getDrugs' endpoint to find the core ingredient (TTY="IN") ---
    try:
        print("Step 1: Attempting to find the core ingredient via getDrugs...")
        url = f"{BASE_URL}/drugs.json?name={drug_name}"
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            data = response.json()
            drug_groups = data.get('drugGroup', {}).get('conceptGroup')
            if drug_groups and isinstance(drug_groups, list):
                for group in drug_groups:
                    if group and group.get("tty") == "IN":
                        concepts = group.get('conceptProperties')
                        if concepts and isinstance(concepts, list) and concepts:
                            rxcui = concepts[0].get("rxcui")
                            tty = concepts[0].get("tty")
                            print(f"  -> SUCCESS (Step 1): Found Ingredient RxCUI: {rxcui} (TTY: {tty})")
                            return rxcui
        print("  -> Step 1 did not find a direct ingredient match.")
    except requests.exceptions.RequestException as e:
        print(f"  -> Step 1 search failed for '{drug_name}': {e}")
        
    # --- Step 2: Fallback to 'approximateTerm' search if Step 1 fails ---
    try:
        print("Step 2: Falling back to approximate (fuzzy) search...")
        url = f"{BASE_URL}/approximateTerm.json?term={drug_name}&maxEntries=4"
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            data = response.json()
            candidates = data.get('approximateGroup', {}).get('candidate')
            if candidates:
                rxcui = _find_best_rxcui_from_candidates(candidates, drug_name)
                if rxcui:
                    print(f"  -> SUCCESS (Step 2): Found best match RxCUI via approximate search: {rxcui}")
                    return rxcui
        print("  -> Step 2 did not find an approximate match.")
    except requests.exceptions.RequestException as e:
        print(f"  -> Step 2 search failed for '{drug_name}': {e}")
        
    # --- Step 3: If all else fails, check for spelling suggestions ---
    try:
        print("Step 3: Checking for spelling suggestions...")
        url = f"{BASE_URL}/spellingsuggestions.json?name={drug_name}"
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            data = response.json()
            suggestions = data.get('suggestionGroup', {}).get('suggestionList', {}).get('suggestion')
            if suggestions and isinstance(suggestions, list) and suggestions[0].lower() != drug_name.lower():
                corrected_name = suggestions[0]
                print(f"  -> Found spelling suggestion: '{corrected_name}'. Restarting search process...")
                return get_rxcui(corrected_name, depth + 1)
        print("  -> Step 3 found no spelling suggestions.")
    except requests.exceptions.RequestException as e:
        print(f"  -> Step 3 check failed for '{drug_name}': {e}")
        
    print(f"--- FINAL resilient search FAILED for drug: '{drug_name}' ---")
    return None

def get_interactions(drug_list: List[str]) -> List[dict]:
    """Gets interactions for a list of drug names."""
    print("\n--- Starting Drug Interaction Check ---")
    rxcuis = [rxcui for drug in drug_list if (rxcui := get_rxcui(drug))]
    
    if len(rxcuis) < 2:
        print("Fewer than two valid drug RxCUIs found. Skipping interaction check.")
        print("-------------------------------------\n")
        return []

    rxcui_str = "+".join(rxcuis)
    print(f"Checking interactions for RxCUIs: {rxcui_str}")
    url = f"{BASE_URL}/interaction/list.json?rxcuis={rxcui_str}"
    
    try:
        response = requests.get(url, timeout=15)
        response.raise_for_status()
        data = response.json()
        
        if 'fullInteractionTypeGroup' not in data:
            print("No interaction data returned from API.")
            print("-------------------------------------\n")
            return []

        results = []
        for group in data['fullInteractionTypeGroup']:
            for interaction_type in group['fullInteractionType']:
                for pair in interaction_type['interactionPair']:
                    interaction_details = {
                        "drugs_involved": [
                            pair['interactionConcept'][0]['minConceptItem']['name'],
                            pair['interactionConcept'][1]['minConceptItem']['name']
                        ],
                        "severity": pair['severity'],
                        "description": pair['description']
                    }
                    results.append(interaction_details)
        
        print(f"Found {len(results)} interactions.")
        print("-------------------------------------\n")
        return results
        
    except requests.exceptions.RequestException as e:
        print(f"Error fetching interactions from API: {e}")
        print("-------------------------------------\n")
        return []

