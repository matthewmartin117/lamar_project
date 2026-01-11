from django.db import models
from django.core.validators import RegexValidator

# --- P0 Validators: Hard-reject impossible formats ---
MRN_VALIDATOR = RegexValidator(r"^\d{6,8}$", "MRN must be between 6 and 8 digits.")
NPI_VALIDATOR = RegexValidator(r"^\d{10}$", "NPI must be exactly 10 digits.")

class Patient(models.Model):
    # We keep MRN unique as our Single Source of Truth
    mrn = models.CharField(max_length=8, unique=True, validators=[MRN_VALIDATOR])
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
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
    # Use only this one definition
    order_date = models.DateField(help_text="The actual date the order was placed.")

    patient_records_text = models.TextField()

    # These match the fields your Form is trying to save
    is_possible_duplicate_order = models.BooleanField(default=False)
    duplicate_reason = models.TextField(blank=True, null=True)

    # For the P0 clinical requirements
    primary_diagnosis_icd10 = models.CharField(max_length=10)
    additional_diagnoses = models.TextField(blank=True)
    medication_history = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["patient", "medication_name", "order_date"],
                name="unique_order_constraint"
            )
        ]

class CarePlan(models.Model):
    order = models.OneToOneField(Order, on_delete=models.CASCADE, related_name="care_plan")
    generated_text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)