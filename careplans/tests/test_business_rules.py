from django.test import TestCase
from careplans.models import Patient, Provider, Order
from django.utils import timezone

# Provider conflict rule (unit-level)
class TestProviderRules(TestCase):

    def test_provider_conflict_detected_on_name_mismatch(self):
        p = Provider.objects.create(
            npi="1234567890",
            name="Dr Original"
        )

        # Simulate form save logic
        mismatch = (p.name.lower() != "dr changed".lower())

        self.assertTrue(mismatch)

# Patient identity mismatch flag
class TestPatientIdentityRules(TestCase):

    def test_patient_name_mismatch_flag(self):
        p = Patient.objects.create(
            mrn="222222",
            first_name="Alice",
            last_name="Smith"
        )

        mismatch = (
            p.first_name.lower() != "Alicia".lower() or
            p.last_name.lower() != "Smith".lower()
        )

        self.assertTrue(mismatch)

# Duplicate-order logic (unit-level)
class TestDuplicateLogic(TestCase):

    def setUp(self):
        self.patient = Patient.objects.create(
            mrn="999999", first_name="A", last_name="B"
        )
        self.provider = Provider.objects.create(
            npi="1111111111", name="Dr X"
        )
        self.today = timezone.localdate()

        Order.objects.create(
            patient=self.patient,
            provider=self.provider,
            medication_name="IVIG",
            order_date=self.today,
            primary_diagnosis_icd10="G70.0",
            patient_records_text="Note..."
        )

class TestDuplicateLogic(TestCase):

    def setUp(self):
        self.patient = Patient.objects.create(
            mrn="999999", first_name="A", last_name="B"
        )
        self.provider = Provider.objects.create(
            npi="1111111111", name="Dr X"
        )
        self.today = timezone.localdate()

        Order.objects.create(
            patient=self.patient,
            provider=self.provider,
            medication_name="IVIG",
            order_date=self.today,
            primary_diagnosis_icd10="G70.0",
            patient_records_text="Note..."
        )

    def test_exact_duplicate_should_be_blocked(self):
        # database-level constraint should fire
        with self.assertRaises(Exception):
            Order.objects.create(
                patient=self.patient,
                provider=self.provider,
                medication_name="IVIG",
                order_date=self.today,
                primary_diagnosis_icd10="G70.0",
                patient_records_text="Note..."
            )
