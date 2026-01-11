from django.test import TestCase

# This proves that the system enforces the “reject impossible formats” rule deterministically.
from django.core.exceptions import ValidationError
from django.test import TestCase
from careplans.models import Patient, Provider, MRN_VALIDATOR, NPI_VALIDATOR


class TestValidationRules(TestCase):

    def test_mrn_rejects_invalid_length(self):
        with self.assertRaises(ValidationError):
            MRN_VALIDATOR("12345")  # only 5 digits

        with self.assertRaises(ValidationError):
            MRN_VALIDATOR("1234567")  # 7 digits — invalid (must be exactly 6)

    def test_npi_rejects_non_10_digit(self):
        with self.assertRaises(ValidationError):
            NPI_VALIDATOR("123")  # too short

        with self.assertRaises(ValidationError):
            NPI_VALIDATOR("12345678901")  # too long

    def test_patient_and_provider_accept_valid_values(self):
        p = Patient.objects.create(
            mrn="123456",
            first_name="John",
            last_name="Doe"
        )
        self.assertEqual(p.mrn, "123456")

        prov = Provider.objects.create(
            npi="1234567890",
            name="Dr Smith"
        )
        self.assertEqual(prov.npi, "1234567890")

