from django.db import models
from django.core.validators import RegexValidator

# --- P0 Validators ---
MRN_VALIDATOR = RegexValidator(r"^\d{6}$", "MRN must be exactly 6 digits.")
NPI_VALIDATOR = RegexValidator(r"^\d{10}$", "NPI must be exactly 10 digits.")
ICD10_VALIDATOR = RegexValidator(
    r"^[A-TV-Z][0-9][A-Z0-9](\.[A-Z0-9]{1,4})?$",
    "Invalid ICD-10 format."
)


class Patient(models.Model):
    # MRN = Single Source of Truth
    mrn = models.CharField(max_length=6, unique=True, validators=[MRN_VALIDATOR])
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)

    # DOB is OPTIONAL (brief does not require it)
    date_of_birth = models.DateField(null=True, blank=True)

    def __str__(self):
        return f"{self.last_name}, {self.first_name} ({self.mrn})"


class Provider(models.Model):
    npi = models.CharField(max_length=10, unique=True, validators=[NPI_VALIDATOR])
    name = models.CharField(max_length=200)

    def __str__(self):
        return f"{self.name} (NPI: {self.npi})"


class Order(models.Model):
    patient = models.ForeignKey(Patient, on_delete=models.PROTECT, related_name="orders")
    provider = models.ForeignKey(Provider, on_delete=models.PROTECT, related_name="orders")

    medication_name = models.CharField(max_length=200)
    order_date = models.DateField(help_text="The actual date the order was placed.")

    # Required for LLM input
    patient_records_text = models.TextField()

    # P0-required clinical fields
    primary_diagnosis_icd10 = models.CharField(max_length=10, validators=[ICD10_VALIDATOR])

    # Store lists properly (per brief)
    additional_diagnoses = models.JSONField(default=list, blank=True)
    medication_history = models.JSONField(default=list, blank=True)

    # Soft duplicate + provider conflict flags
    is_possible_duplicate_order = models.BooleanField(default=False)
    duplicate_reason = models.TextField(blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            # HARD duplicate rule (block)
            models.UniqueConstraint(
                fields=["patient", "medication_name", "order_date"],
                name="unique_order_constraint",
            )
        ]

    def __str__(self):
        return f"Order for {self.patient.mrn} - {self.medication_name} on {self.order_date}"


class CarePlan(models.Model):
    order = models.OneToOneField(Order, on_delete=models.CASCADE, related_name="care_plan")
    generated_text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"CarePlan for Order {self.order.id}"
