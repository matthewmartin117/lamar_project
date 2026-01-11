import os
from openai import OpenAI
from django.conf import settings

def generate_care_plan_from_llm(patient_records_text: str, medication_name: str):
    """
    Generate a pharmacist care plan from clinical text using an LLM.

    Returns:
        (care_plan_text, error_message)
    """
    # Initialize INSIDE the function so it doesn't crash on startup
    api_key = getattr(settings, "OPENAI_API_KEY", None)
    if not api_key:
        return None, "API Key missing. Please check system configuration."

    system_prompt = (
        "You are a Senior Clinical Pharmacist at a specialty pharmacy. "
        "Your task is to transform unstructured clinical notes into a structured Pharmacist Care Plan. "
        "CRITICAL RULE: You must extract the patient's Date of Birth (DOB) and ensure it is formatted as YYYY-MM-DD. "
        "If the DOB is invalid or missing, explicitly flag this in the Problem List."
    )

    user_prompt = f"""
    ### INPUT TEMPLATE REFERENCE
    Follow this structure when extracting data:
    - Name, MRN, DOB (YYYY-MM-DD)
    - Primary/Secondary Diagnoses (ICD-10 when available)
    - Medication History & Home Meds
    - Clinical Status & Vitals

    ### OUTPUT TEMPLATE REQUIREMENTS
    Produce exactly these sections:

    1. Problem List / Drug Therapy Problems (DTPs)
    2. SMART Goals (Primary, Safety, and Process goals)
    3. Pharmacist Interventions (Dosing, Premeds, Titration, Hydration, Interactions)
    4. Monitoring Plan & Lab Schedule

    ### PATIENT RECORDS TO PROCESS
    Medication Requested: {medication_name}

    Records:
    {patient_records_text}
    """

    try:
        client = OpenAI(api_key=api_key)
        response = client.responses.create(
            model="gpt-4o",
            input=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            # protect against token overflow
            max_output_tokens=800,
            # for determinstic output
            temperature=0.2,
            # make sure the model returns text and not JSON
            response_format={"type": "text"},
            # makes sure repsonse is not lagging
            timeout=20,
        )

        care_plan_text = response.output_text
        return care_plan_text, None

    except Exception as e:
        # P0: Fail gracefully without leaking server internals
        print(f"LLM Error: {str(e)}")
        return None, "The AI service failed to generate the care plan. The order has still been saved."
