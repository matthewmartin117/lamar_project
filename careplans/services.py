import os
import logging
from openai import OpenAI
from django.conf import settings

logger = logging.getLogger(__name__)

def generate_care_plan_from_llm(patient_records_text: str, medication_name: str):
    # 1. Initialize inside to prevent startup crashes
    api_key = getattr(settings, "OPENAI_API_KEY", None)
    if not api_key:
        return None, "API Key missing. Please check system configuration."

    # PRESERVED: Your high-detail clinical prompts
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

        # FIX: Changed 'responses.create' to 'chat.completions.create'
        # FIX: Changed 'input' to 'messages'
        # FIX: Changed 'max_output_tokens' to 'max_tokens'
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            max_tokens=800,  # Standard param for Chat Completions
            temperature=0.2,
            response_format={"type": "text"},
            timeout=20, # Note: some older httpx versions handle this differently
        )

        # FIX: Access the text via choices[0].message.content
        care_plan_text = response.choices[0].message.content
        return care_plan_text, None

    except Exception as e:
        logger.error(f"LLM integration failed: {e}")
        return None, "The AI service is currently unavailable. The order has been saved."