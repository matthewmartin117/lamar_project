from django import forms
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from .models import Provider, Patient, Order


class OrderIntakeForm(forms.Form):
    # Provider
    provider_name = forms.CharField(max_length=200, label="Provider Name")
    provider_npi = forms.CharField(max_length=10, label="Provider NPI")

    # Patient
    patient_first_name = forms.CharField(max_length=100, label="Patient First Name")
    patient_last_name = forms.CharField(max_length=100, label="Patient Last Name")
    patient_mrn = forms.CharField(max_length=6, label="Patient MRN")
    patient_dob = forms.DateField(required=False, label="Patient DOB")

    # Order
    medication_name = forms.CharField(max_length=200, label="Medication Name")
    order_date = forms.DateField(label="Order Date")
    primary_diagnosis_icd10 = forms.CharField(max_length=10, label="Primary Diagnosis (ICD-10)")

    additional_diagnoses = forms.CharField(
        required=False,
        help_text="Comma-separated ICD-10 codes"
    )
    medication_history = forms.CharField(
        required=False,
        help_text="Comma-separated medication strings"
    )

    patient_records_text = forms.CharField(widget=forms.Textarea)

    # prevents PHI leaks
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        for field in self.fields.values():
            # Prevent autofill, but allow paste
            field.widget.attrs['autocomplete'] = 'new-password'
            field.widget.attrs['autocapitalize'] = 'none'
            field.widget.attrs['autocorrect'] = 'off'
            field.widget.attrs['spellcheck'] = 'false'



    # ---------------------
    # Field-level validation
    # ---------------------

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
        if d > timezone.localdate():
            raise ValidationError("Order date cannot be in the future.")
        return d

    # ---------------------
    # Cross-field validation
    # ---------------------
    def clean(self):
        cleaned = super().clean()
        if self.errors:
            return cleaned

        mrn = cleaned["patient_mrn"]
        med = cleaned["medication_name"].strip()
        date = cleaned["order_date"]

        # HARD duplicate — block
        existing = Order.objects.filter(
            patient__mrn=mrn,
            medication_name__iexact=med,
            order_date=date,
        )
        if existing.exists():
            raise ValidationError(
                "Duplicate order: same patient MRN, same medication, same date."
            )

        # SOFT duplicate — allow with flag
        soft = Order.objects.filter(
            patient__mrn=mrn,
            medication_name__iexact=med,
        ).exclude(order_date=date)
        cleaned["__possible_duplicate_order"] = soft.exists()

        # Provider conflicts
        name = cleaned["provider_name"].strip()
        npi = cleaned["provider_npi"]
        provider_by_name = Provider.objects.filter(name__iexact=name).first()

        # Only flag when **same name but different NPI**
        if provider_by_name and provider_by_name.npi != npi:
            cleaned["__provider_npi_conflict"] = True
        else:
            cleaned["__provider_npi_conflict"] = False

        return cleaned

    # ---------------------
    # Save() Implementation
    # ---------------------
    def save(self):
        if not self.is_valid():
            raise ValueError("Cannot save invalid form")

        cd = self.cleaned_data

        # Convert comma-separated → list for JSONField
        addl_dx = [d.strip() for d in cd["additional_diagnoses"].split(",") if d.strip()]
        med_hist = [m.strip() for m in cd["medication_history"].split(",") if m.strip()]

        with transaction.atomic():

            # Provider creation
            provider, _ = Provider.objects.get_or_create(
                npi=cd["provider_npi"],
                defaults={"name": cd["provider_name"].strip()},
            )

            provider_name_mismatch = False
            # Name mismatch only matters if NPI matched an existing provider
            if provider.name.lower() != cd["provider_name"].strip().lower():
                provider_name_mismatch = True

            # Patient creation
            patient, _ = Patient.objects.get_or_create(
                mrn=cd["patient_mrn"],
                defaults={
                    "first_name": cd["patient_first_name"].strip(),
                    "last_name": cd["patient_last_name"].strip(),
                    "date_of_birth": cd.get("patient_dob"),
                },
            )

            patient_name_mismatch = (
                patient.first_name.lower() != cd["patient_first_name"].strip().lower() or
                patient.last_name.lower() != cd["patient_last_name"].strip().lower()
            )

            order = Order.objects.create(
                patient=patient,
                provider=provider,
                medication_name=cd["medication_name"].strip(),
                order_date=cd["order_date"],
                primary_diagnosis_icd10=cd["primary_diagnosis_icd10"].strip(),
                additional_diagnoses=addl_dx,
                medication_history=med_hist,
                patient_records_text=cd["patient_records_text"],
                is_possible_duplicate_order=cd.get("__possible_duplicate_order", False),
                duplicate_reason=self._build_reason(
                    cd,
                    provider_name_mismatch,
                    patient_name_mismatch
                ),
            )

        return order

    def _build_reason(self, cd, provider_name_mismatch, patient_name_mismatch):
        reasons = []
        if cd.get("__possible_duplicate_order"):
            reasons.append("Possible duplicate order (same patient + medication on a different date).")
        if cd.get("__provider_npi_conflict"):
            reasons.append("Provider name matches existing provider but NPI differs.")
        if provider_name_mismatch:
            reasons.append("Provider NPI matches existing record but has a different provider name.")
        if patient_name_mismatch:
            reasons.append("Patient MRN exists but name differs.")
        return " | ".join(reasons)
