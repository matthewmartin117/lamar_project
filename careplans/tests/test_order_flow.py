from django.test import TestCase
from careplans.forms import OrderIntakeForm
from careplans.models import Order, Patient, Provider
from django.utils import timezone

"""
(Integration test: full form flow + duplicate block logic)

This directly proves P0 logic:

Hard duplicates are blocked

Allowed-but-flagged duplicates are saved

Provider conflict warnings do not block saving
"""

class TestOrderFlow(TestCase):

    def setUp(self):
        # A baseline patient & provider
        self.patient = Patient.objects.create(
            mrn="123456",
            first_name="Alice",
            last_name="Gray"
        )

        self.provider = Provider.objects.create(
            npi="1111111111",
            name="Dr House"
        )

        # A baseline valid payload
        self.base_payload = {
            "provider_name": "Dr House",
            "provider_npi": "1111111111",
            "patient_first_name": "Alice",
            "patient_last_name": "Gray",
            "patient_mrn": "123456",
            "patient_dob": "1980-01-01",
            "medication_name": "IVIG",
            "order_date": timezone.localdate(),
            "primary_diagnosis_icd10": "G70.0",
            "additional_diagnoses": "I10",
            "medication_history": "Pyridostigmine",
            "patient_records_text": "Clinical notes...",
        }

    def test_valid_order_creates_successfully(self):
        form = OrderIntakeForm(data=self.base_payload)
        self.assertTrue(form.is_valid(), form.errors)

        order = form.save()
        self.assertIsInstance(order, Order)
        self.assertEqual(order.patient.mrn, "123456")
        self.assertFalse(order.is_possible_duplicate_order)

    def test_hard_duplicate_same_patient_same_med_same_date(self):
        # Create the initial order
        form1 = OrderIntakeForm(data=self.base_payload)
        self.assertTrue(form1.is_valid(), form1.errors)
        form1.save()

        # Second identical order should fail validation
        form2 = OrderIntakeForm(data=self.base_payload)
        self.assertFalse(form2.is_valid())
        self.assertIn("Duplicate order", str(form2.errors))

    def test_soft_duplicate_same_patient_same_med_different_date(self):
        # First order
        form1 = OrderIntakeForm(data=self.base_payload)
        self.assertTrue(form1.is_valid(), form1.errors)
        order1 = form1.save()

        # Modify date only
        payload2 = self.base_payload.copy()
        payload2["order_date"] = timezone.localdate().replace(day=1)

        form2 = OrderIntakeForm(data=payload2)
        self.assertTrue(form2.is_valid(), form2.errors)

        order2 = form2.save()
        self.assertTrue(order2.is_possible_duplicate_order)
        self.assertIn("Possible duplicate", order2.duplicate_reason)

    def test_provider_name_npi_conflict_allows_save_with_flag(self):
        # Existing provider has NPI=1111111111, name="Dr House"
        new_payload = self.base_payload.copy()
        new_payload["provider_name"] = "Dr SomeoneElse"  # mismatch name
        new_payload["provider_npi"] = "1111111111"       # same NPI

        form = OrderIntakeForm(data=new_payload)
        self.assertTrue(form.is_valid(), form.errors)

        order = form.save()
        self.assertIn("different provider name", order.duplicate_reason)
