from django import forms
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from .models import Provider, Patient, Order


class OrderIntakeForm(forms.Form):
    # Provider
    provider_name = forms.CharField(max_length=200)
    provider_npi = forms.CharField(max_length=10)

    # Patient
    patient_first_name = forms.CharField(max_length=100)
    patient_last_name = forms.CharField(max_length=100)
    patient_mrn = forms.CharField(max_length=6)
    patient_dob = forms.DateField()

    # Order
    medication_name = forms.CharField(max_length=200)
    order_date = forms.DateField()
    primary_diagnosis_icd10 = forms.CharField(max_length=10)
    additional_diagnoses = forms.CharField(
        required=False,
        help_text="Comma-separated ICD-10 codes"
    )
    medication_history = forms.CharField(
        required=False,
        help_text="Comma-separated medication strings"
    )
    patient_records_text = forms.CharField(widget=forms.Textarea)

    def clean_provider_npi(self):
        npi = self.cleaned_data["provider_npi"].strip()
        if not (npi.isdigit() and len(npi) == 10):
            raise ValidationError("NPI must be exactly 10 digits.")
        return npi

    def clean_patient_mrn(self):
        mrn = self.cleaned_data["patient_mrn"].strip()
        if not (mrn.isdigit() and len(mrn) == 6):
            raise ValidationError("MRN must be exactly 6 digits.")
        return mrn

    def clean_order_date(self):
        d = self.cleaned_data["order_date"]
        # Optional: prevent future dates if you want (ask if needed)
        if d > timezone.localdate():
            raise ValidationError("Order date cannot be in the future.")
        return d

    def clean(self):
        """
        Cross-field validation.
        This runs AFTER individual clean_<field>() methods.
        """
        cleaned = super().clean()
        if self.errors:
            return cleaned  # stop early if basic fields invalid

        mrn = cleaned["patient_mrn"]
        order_date = cleaned["order_date"]
        med = cleaned["medication_name"].strip().lower()

        # Duplicate order detection (hard-block)
        # Needs patient existence; but we can check by MRN since MRN is unique identifier.
        existing_orders = Order.objects.filter(
            patient__mrn=mrn,
            order_date=order_date,
            medication_name__iexact=cleaned["medication_name"].strip(),
        )
        if existing_orders.exists():
            raise ValidationError("Duplicate order: same patient MRN, same medication, same date.")

        # Potential duplicate (allow + flag)
        possible_dup = Order.objects.filter(
            patient__mrn=mrn,
            medication_name__iexact=cleaned["medication_name"].strip(),
        ).exclude(order_date=order_date)
        cleaned["__possible_duplicate_order"] = possible_dup.exists()

        # Provider NPI conflict logic (allow + flag)
        # If provider exists by name but NPI differs, allow but flag.
        name = cleaned["provider_name"].strip()
        npi = cleaned["provider_npi"]
        provider_by_name = Provider.objects.filter(name__iexact=name).first()
        if provider_by_name and provider_by_name.npi != npi:
            cleaned["__provider_npi_conflict"] = True
        else:
            cleaned["__provider_npi_conflict"] = False

        return cleaned

    def save(self):
        """
        Create Provider, Patient, and Order safely.
        Use a transaction so we never partially write.
        """
        if not self.is_valid():
            raise ValueError("Cannot save invalid form")

        cd = self.cleaned_data

        with transaction.atomic():
            provider, provider_created = Provider.objects.get_or_create(
                npi=cd["provider_npi"],
                defaults={"name": cd["provider_name"].strip()},
            )

            # If same NPI but different name, allow + flag via order notes
            provider_name_mismatch = (provider.name.lower() != cd["provider_name"].strip().lower())

            patient, patient_created = Patient.objects.get_or_create(
                mrn=cd["patient_mrn"],
                defaults={
                    "first_name": cd["patient_first_name"].strip(),
                    "last_name": cd["patient_last_name"].strip(),
                },
            )

            # If MRN exists but names differ, allow + flag (do not block)
            patient_name_mismatch = (
                patient.first_name.lower() != cd["patient_first_name"].strip().lower()
                or patient.last_name.lower() != cd["patient_last_name"].strip().lower()
            )

            order = Order.objects.create(
                patient=patient,
                provider=provider,
                medication_name=cd["medication_name"].strip(),
                order_date=cd["order_date"],
                primary_diagnosis_icd10=cd["primary_diagnosis_icd10"].strip(),
                additional_diagnoses=cd["additional_diagnoses"],
                medication_history=cd["medication_history"],
                patient_records_text=cd["patient_records_text"],
                is_possible_duplicate_order=bool(cd.get("__possible_duplicate_order", False)),
                duplicate_reason=self._build_reason(
                    cd,
                    provider_name_mismatch,
                    patient_name_mismatch
                ),
            )

        return order

    def _build_reason(self, cd, provider_name_mismatch, patient_name_mismatch) -> str:
        reasons = []
        if cd.get("__possible_duplicate_order"):
            reasons.append("Possible duplicate: same patient + med exists on different date.")
        if cd.get("__provider_npi_conflict"):
            reasons.append("Provider name exists with different NPI (flagged per spec).")
        if provider_name_mismatch:
            reasons.append("Same NPI entered with different provider name.")
        if patient_name_mismatch:
            reasons.append("Same MRN entered with different patient name.")
        return " | ".join(reasons)
