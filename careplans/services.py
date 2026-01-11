import os
from openai import OpenAI

# It's best practice to use environment variables for keys
# export OPENAI_API_KEY='your-key-here'
client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

# service to generate care plan
def generate_care_plan_from_llm(patient_records_text, medication_name):
    """
    Connects to OpenAI to generate a clinical care plan.
    """
    try:
        # P0 Requirement: Errors are contained and safe
        response = client.chat.completions.create(
            model="gpt-4o", # Or "gpt-3.5-turbo" for cost efficiency
            messages=[
                {"role": "system", "content": "You are a clinical pharmacist. Generate a concise 5-day care plan for the requested medication based on the provided clinical records."},
                {"role": "user", "content": f"Medication: {medication_name}\n\nRecords: {patient_records_text}"}
            ],
            timeout=15.0 # Ensure the app doesn't hang forever
        )
        return response.choices[0].message.content, None

    except Exception as e:
        # Log the real error for the engineer, but return a safe message for the UI
        print(f"LLM Error: {e}")
        return None, "The AI service is currently unavailable. The order was saved, but the care plan must be generated manually."