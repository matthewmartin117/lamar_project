from django.db import models
from django.core.validators import RegexValidator


class Patient(models.Model):
    # MRN is explicitly defined as unique 6-digit number in the brief
    mrn = models.CharField(
        max_length=6,
        unique=True,
        validators=[
            RegexValidator(regex=r"^\d{6}$", message="MRN must be exactly 6 digits.")
        ],
        help_text="Unique 6-digit medical record number."
    )

    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)

    # DOB wasn't in your original input list, but production-ready examples mention DOB validation.
    # If Lamar didn't want DOB, you can remove it. For now, I recommend adding it.
    date_of_birth = models.DateField(null=True, blank=True)

    primary_diagnosis_icd10 = models.CharField(
        max_length=10,
        help_text="Primary ICD-10 code (format validation can be added later)."
    )

    def __str__(self) -> str:
        return f"{self.last_name}, {self.first_name} (MRN {self.mrn})"


class Provider(models.Model):
    # NPI is exactly 10-digit number
    npi = models.CharField(
        max_length=10,
        unique=True,
        validators=[
            RegexValidator(regex=r"^\d{10}$", message="NPI must be exactly 10 digits.")
        ],
        help_text="10-digit National Provider Identifier."
    )

    name = models.CharField(max_length=200)

    def __str__(self) -> str:
        return f"{self.name} (NPI {self.npi})"


class Order(models.Model):
    patient = models.ForeignKey(Patient, on_delete=models.PROTECT, related_name="orders")
    provider = models.ForeignKey(Provider, on_delete=models.PROTECT, related_name="orders")

    medication_name = models.CharField(max_length=200)
    order_date = models.DateField()

    additional_diagnoses = models.JSONField(default=list, blank=True)
    medication_history = models.JSONField(default=list, blank=True)

    patient_records_text = models.TextField()

    # “flag but don’t block” case: same patient + same med on different date
    duplicate_warning = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            # Hard duplicate: same patient, same med, same date -> BLOCK
            models.UniqueConstraint(
                fields=["patient", "medication_name", "order_date"],
                name="uniq_order_patient_med_date"
            )
        ]

    def __str__(self) -> str:
        return f"Order: {self.patient.mrn} {self.medication_name} ({self.order_date})"


class CarePlan(models.Model):
    order = models.OneToOneField(Order, on_delete=models.CASCADE, related_name="care_plan")
    generated_text = models.TextField()

    llm_model = models.CharField(max_length=100, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return f"CarePlan for {self.order}"





