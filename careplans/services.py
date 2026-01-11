import os
from openai import OpenAI

client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

def generate_care_plan_from_llm(patient_records_text, medication_name):
    # PROMPT CONSTRUCTION
    system_prompt = (
        "You are a Senior Clinical Pharmacist at a specialty pharmacy. "
        "Your task is to transform unstructured clinical notes into a structured Pharmacist Care Plan. "
        "CRITICAL RULE: You must extract the Date of Birth (DOB) and ensure it is formatted as YYYY-MM-DD. "
        "If the DOB in the records is invalid or missing, flag it in the 'Problem List'."
    )

    user_prompt = f"""
    ### INPUT TEMPLATE REFERENCE
    Use the following structure to parse the clinical records:
    - Name, MRN, DOB (YYYY-MM-DD)
    - Primary/Secondary Diagnoses (ICD-10 preferred)
    - Medication History & Home Meds
    - Clinical Status & Vitals

    ### OUTPUT TEMPLATE REFERENCE
    Your response must follow this exact sections:
    1. Problem List / Drug Therapy Problems (DTPs)
    2. SMART Goals (Primary, Safety, and Process)
    3. Pharmacist Interventions (Dosing, Premeds, Titration, Hydration)
    4. Monitoring Plan & Lab Schedule

    ### PATIENT RECORDS TO PROCESS
    Medication Requested: {medication_name}
    Records:
    {patient_records_text}
    """

    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.2, # Lower temperature = more deterministic and stable output
            timeout=20.0
        )
        return response.choices[0].message.content, None

    except Exception as e:
        # P0: Fail gracefully without leaking internals
        print(f"LLM Error: {str(e)}")
        return None, "The AI service failed to generate the care plan. The order is saved."