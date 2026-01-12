# Lamar Health: Specialty Pharmacy Care Plan Engine (P0 Build)

**Author:** Matthew Martin
**Role:** Forward Deployed Engineer (FDE) Candidate
**Status:** Production-Ready P0 Implementation

---

## 1. Executive Summary
This system is an end-to-end intake engine designed to transform unstructured clinical notes into structured, validated Pharmacist Care Plans. It replaces a manual 40-minute process with a deterministic workflow that prioritizes **Data Integrity** and **Graceful Failure**.

## 2. P0 Design Decisions (The "Senior" Approach)
In this build, I prioritized **backend robustness** over frontend aesthetics to meet the "Production-Ready" signal.

* **Deterministic Integrity:** Validation happens at the Form layer (UI) and is enforced at the Database layer (Postgres). This prevents "silent failures" or inconsistent states.
* **Service Layer Architecture:** LLM logic is isolated in `services.py`. This ensures that external API latency or failures cannot block database transactions or crash the user session.
* **Atomic Transactions:** All saves (Patient, Provider, Order) are wrapped in a single database transaction. We never leave "half-created" records if a downstream step fails.
* **Safe Error Handling:** No stack traces or PHI are ever exposed to the end-user. Errors are trapped, logged, and surfaced as actionable messages.

---

## 3. System Architecture
The project follows a modular Django MVT (Model-View-Template) structure to ensure the code is navigable by any engineer in minutes.

```text
careplans/
├── models.py          # Strict schema with Database Constraints
├── forms.py           # Multi-entity validation (The "Security Guard")
├── services.py        # Isolated LLM & External API logic
├── views.py           # Request orchestration & User messaging
├── tests.py           # Integrity & Business Rule verification
└── templates/         # Functional UI with Bootstrap styling
```
---

## 4. Integrity Rules & Validation
This system implements a "Defense in Depth" strategy where validation is redundant across layers to ensure zero data corruption.

### Hard-Blocks (Deterministic Rejection)
* **Duplicate Therapy Prevention:** The system physically rejects any submission where the (Patient MRN + Medication Name + Order Date) matches an existing record.
* **Structural Integrity:** Regex validators enforce that NPIs are exactly 10 digits and MRNs are 6 digits before the database is even queried.
* **Temporal Logic:** The `clean_order_date` method ensures backlogged data is a valid past date and prevents future-dated "impossible" orders.

### Soft-Warnings (Flagged & Persisted)
* **Identity Collision:** If an MRN exists but the name differs (e.g., "Jon" vs "John"), the system saves the record but logs a `patient_name_mismatch` flag for pharmacist review.
* **Provider Mismatch:** If an NPI is valid but the provider name has changed, the discrepancy is captured in the `integrity_warnings` field.
* **Therapy Overlap:** If the same patient/medication exists on a different date, it is flagged as a potential duplicate fill.

---

## 5. LLM Integration
The Care Plan generation is designed as an isolated **Service Layer** to maintain high system availability even during external API downtime.

* **Prompt Engineering:** Uses **Few-Shot Prompting** with explicit Input/Output templates to force the LLM into a structured clinical format.
* **Deterministic Configuration:** Configured with a `temperature` of 0.2 to ensure output consistency and clinical reliability.
* **Graceful Failure:** The LLM call is wrapped in a `try/except` block with a 15-second timeout. If the AI fails, the `Order` remains safely saved, and the user is notified to generate the plan manually.


---

## 6. Setup & Deployment

### Prerequisites
- Python 3.11+
- Postgres (recommended for running the app locally)
- Tests run out of the box without Postgres (SQLite in-memory during `manage.py test`)

---

### 6.1 Create and activate a virtual environment

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

---

### 6.2 Environment variables

Create a `.env` file in the project root (do **not** commit this file):

```env
OPENAI_API_KEY=your_key_here
DEBUG=True
DB_NAME=lamar_db
DB_USER=lamar_user
DB_PASSWORD=lamar_password
DB_HOST=localhost
DB_PORT=5432
```

---

### 6.3 Postgres setup (for running the app)

```bash
psql -U postgres -c "CREATE USER lamar_user WITH PASSWORD 'lamar_password' CREATEDB;"
psql -U postgres -c "CREATE DATABASE lamar_db OWNER lamar_user;"
```

---

### 6.4 Migrations and runserver

```bash
python manage.py migrate
python manage.py runserver
```

Then open in your browser:

[http://127.0.0.1:8000/intake/](http://127.0.0.1:8000/intake/)

---

### 6.5 Run tests

```bash
python manage.py test
```

> Note: The test suite automatically switches to an **in-memory SQLite** database when running `manage.py test`, so reviewers can run tests without configuring Postgres.

---


## 7. Known Limitations & Future Scope (P1/P2)
- Async Processing: In production, LLM calls should move to a background worker (Celery) to improve UI responsiveness.
- Identity Resolution: Future iterations would move from strict MRN matching to fuzzy-matching for patient identities.
- PDF Ingestion: P1 goal to add OCR and pre-parsing of clinical notes before LLM submission.
