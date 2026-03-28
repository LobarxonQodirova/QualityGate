"""
Tests for the inspections app.
Covers models, serializers, views, and business logic.
"""

import uuid
from datetime import timedelta
from unittest.mock import patch

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient, APITestCase

from apps.accounts.models import User
from apps.inspections.models import (
    Inspection,
    InspectionChecklist,
    InspectionItem,
    InspectionResult,
)


class InspectionChecklistModelTest(TestCase):
    """Tests for InspectionChecklist model."""

    def setUp(self):
        self.user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="TestPass1234!",
            first_name="Test",
            last_name="User",
            role=User.Role.QUALITY_ENGINEER,
        )
        self.checklist = InspectionChecklist.objects.create(
            name="Incoming Material Checklist",
            code="CL-2026-001",
            checklist_type=InspectionChecklist.ChecklistType.INCOMING,
            product_line="Raw Materials",
            revision="1.0",
            created_by=self.user,
        )

    def test_str_representation(self):
        self.assertEqual(
            str(self.checklist),
            "CL-2026-001 - Incoming Material Checklist (Rev 1.0)",
        )

    def test_item_count_property(self):
        self.assertEqual(self.checklist.item_count, 0)
        InspectionItem.objects.create(
            checklist=self.checklist,
            sequence=1,
            characteristic="Surface finish",
            measurement_type=InspectionItem.MeasurementType.VISUAL,
        )
        InspectionItem.objects.create(
            checklist=self.checklist,
            sequence=2,
            characteristic="Diameter",
            measurement_type=InspectionItem.MeasurementType.MEASUREMENT,
            nominal_value=25.0,
            upper_spec_limit=25.1,
            lower_spec_limit=24.9,
            unit_of_measure="mm",
        )
        self.assertEqual(self.checklist.item_count, 2)


class InspectionModelTest(TestCase):
    """Tests for Inspection model."""

    def setUp(self):
        self.inspector = User.objects.create_user(
            username="inspector1",
            email="inspector@example.com",
            password="TestPass1234!",
            first_name="Jane",
            last_name="Inspector",
            role=User.Role.INSPECTOR,
        )
        self.checklist = InspectionChecklist.objects.create(
            name="Final Inspection",
            code="CL-FIN-001",
            checklist_type=InspectionChecklist.ChecklistType.FINAL,
            created_by=self.inspector,
        )
        self.item_pass_fail = InspectionItem.objects.create(
            checklist=self.checklist,
            sequence=1,
            characteristic="Label present",
            measurement_type=InspectionItem.MeasurementType.PASS_FAIL,
        )
        self.item_measurement = InspectionItem.objects.create(
            checklist=self.checklist,
            sequence=2,
            characteristic="Weight",
            measurement_type=InspectionItem.MeasurementType.MEASUREMENT,
            nominal_value=100.0,
            upper_spec_limit=102.0,
            lower_spec_limit=98.0,
            unit_of_measure="g",
            is_critical=True,
        )

    def test_auto_number_generation(self):
        inspection = Inspection.objects.create(
            checklist=self.checklist,
            product_name="Widget A",
            inspector=self.inspector,
        )
        self.assertTrue(inspection.inspection_number.startswith("INS-"))
        self.assertEqual(len(inspection.inspection_number.split("-")), 3)

    def test_pass_rate_all_conforming(self):
        inspection = Inspection.objects.create(
            checklist=self.checklist,
            product_name="Widget A",
            inspector=self.inspector,
        )
        InspectionResult.objects.create(
            inspection=inspection,
            inspection_item=self.item_pass_fail,
            is_conforming=True,
            recorded_by=self.inspector,
        )
        InspectionResult.objects.create(
            inspection=inspection,
            inspection_item=self.item_measurement,
            measured_value=100.5,
            is_conforming=True,
            recorded_by=self.inspector,
        )
        self.assertEqual(inspection.pass_rate, 100.0)

    def test_pass_rate_with_failure(self):
        inspection = Inspection.objects.create(
            checklist=self.checklist,
            product_name="Widget B",
            inspector=self.inspector,
        )
        InspectionResult.objects.create(
            inspection=inspection,
            inspection_item=self.item_pass_fail,
            is_conforming=True,
            recorded_by=self.inspector,
        )
        InspectionResult.objects.create(
            inspection=inspection,
            inspection_item=self.item_measurement,
            measured_value=105.0,
            is_conforming=False,
            defect_description="Out of spec",
            recorded_by=self.inspector,
        )
        self.assertEqual(inspection.pass_rate, 50.0)
        self.assertEqual(inspection.total_defects_found, 1)

    def test_pass_rate_no_results(self):
        inspection = Inspection.objects.create(
            checklist=self.checklist,
            product_name="Widget C",
            inspector=self.inspector,
        )
        self.assertIsNone(inspection.pass_rate)


class InspectionResultAutoConformanceTest(TestCase):
    """Tests for auto-conformance calculation in InspectionResult.save()."""

    def setUp(self):
        self.user = User.objects.create_user(
            username="eng1",
            email="eng1@example.com",
            password="TestPass1234!",
            role=User.Role.QUALITY_ENGINEER,
        )
        self.checklist = InspectionChecklist.objects.create(
            name="Dimensional Check",
            code="CL-DIM-001",
            checklist_type=InspectionChecklist.ChecklistType.IN_PROCESS,
            created_by=self.user,
        )
        self.item = InspectionItem.objects.create(
            checklist=self.checklist,
            sequence=1,
            characteristic="Length",
            measurement_type=InspectionItem.MeasurementType.MEASUREMENT,
            nominal_value=50.0,
            upper_spec_limit=50.5,
            lower_spec_limit=49.5,
            unit_of_measure="mm",
        )
        self.inspection = Inspection.objects.create(
            checklist=self.checklist,
            product_name="Bracket",
            inspector=self.user,
        )

    def test_in_spec_measurement(self):
        result = InspectionResult(
            inspection=self.inspection,
            inspection_item=self.item,
            measured_value=50.2,
            recorded_by=self.user,
        )
        result.save()
        self.assertTrue(result.is_conforming)
        self.assertAlmostEqual(result.deviation, 0.2, places=5)

    def test_above_usl(self):
        result = InspectionResult(
            inspection=self.inspection,
            inspection_item=self.item,
            measured_value=51.0,
            recorded_by=self.user,
        )
        result.save()
        self.assertFalse(result.is_conforming)
        self.assertAlmostEqual(result.deviation, 1.0, places=5)

    def test_below_lsl(self):
        result = InspectionResult(
            inspection=self.inspection,
            inspection_item=self.item,
            measured_value=49.0,
            recorded_by=self.user,
        )
        result.save()
        self.assertFalse(result.is_conforming)
        self.assertAlmostEqual(result.deviation, -1.0, places=5)

    def test_exactly_at_usl(self):
        result = InspectionResult(
            inspection=self.inspection,
            inspection_item=self.item,
            measured_value=50.5,
            recorded_by=self.user,
        )
        result.save()
        self.assertTrue(result.is_conforming)


class InspectionAPITest(APITestCase):
    """Tests for inspection API endpoints."""

    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username="api_user",
            email="api@example.com",
            password="TestPass1234!",
            first_name="API",
            last_name="User",
            role=User.Role.INSPECTOR,
        )
        self.client.force_authenticate(user=self.user)

        self.checklist = InspectionChecklist.objects.create(
            name="API Test Checklist",
            code="CL-API-001",
            checklist_type=InspectionChecklist.ChecklistType.FINAL,
            created_by=self.user,
        )

    def test_create_inspection(self):
        url = reverse("inspection-list")
        data = {
            "checklist": str(self.checklist.id),
            "product_name": "API Widget",
            "part_number": "PN-001",
            "batch_number": "BATCH-2026-01",
            "lot_size": 500,
            "sample_size": 50,
            "inspector": str(self.user.id),
        }
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn("id", response.data)
        self.assertEqual(response.data["product_name"], "API Widget")

    def test_list_inspections(self):
        Inspection.objects.create(
            checklist=self.checklist,
            product_name="Widget 1",
            inspector=self.user,
        )
        Inspection.objects.create(
            checklist=self.checklist,
            product_name="Widget 2",
            inspector=self.user,
        )
        url = reverse("inspection-list")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(response.data["count"], 2)

    def test_start_inspection(self):
        inspection = Inspection.objects.create(
            checklist=self.checklist,
            product_name="Widget Start",
            inspector=self.user,
            status=Inspection.Status.PLANNED,
        )
        url = reverse("inspection-start-inspection", args=[str(inspection.id)])
        response = self.client.post(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        inspection.refresh_from_db()
        self.assertEqual(inspection.status, Inspection.Status.IN_PROGRESS)
        self.assertIsNotNone(inspection.started_at)

    def test_start_non_planned_inspection_fails(self):
        inspection = Inspection.objects.create(
            checklist=self.checklist,
            product_name="Widget Running",
            inspector=self.user,
            status=Inspection.Status.IN_PROGRESS,
            started_at=timezone.now(),
        )
        url = reverse("inspection-start-inspection", args=[str(inspection.id)])
        response = self.client.post(url)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_complete_inspection_auto_disposition(self):
        inspection = Inspection.objects.create(
            checklist=self.checklist,
            product_name="Widget Complete",
            inspector=self.user,
            status=Inspection.Status.IN_PROGRESS,
            started_at=timezone.now(),
        )
        item = InspectionItem.objects.create(
            checklist=self.checklist,
            sequence=1,
            characteristic="Visual check",
            measurement_type=InspectionItem.MeasurementType.PASS_FAIL,
        )
        InspectionResult.objects.create(
            inspection=inspection,
            inspection_item=item,
            is_conforming=True,
            recorded_by=self.user,
        )
        url = reverse("inspection-complete-inspection", args=[str(inspection.id)])
        response = self.client.post(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        inspection.refresh_from_db()
        self.assertEqual(inspection.status, Inspection.Status.COMPLETED)
        self.assertEqual(inspection.disposition, Inspection.Disposition.ACCEPT)

    def test_unauthenticated_access_denied(self):
        self.client.force_authenticate(user=None)
        url = reverse("inspection-list")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class InspectionChecklistAPITest(APITestCase):
    """Tests for checklist API endpoints."""

    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username="checklist_user",
            email="checklist@example.com",
            password="TestPass1234!",
            role=User.Role.QUALITY_ENGINEER,
        )
        self.client.force_authenticate(user=self.user)

    def test_create_checklist_with_items(self):
        url = reverse("checklist-list")
        data = {
            "name": "New Process Checklist",
            "code": "CL-NEW-001",
            "checklist_type": InspectionChecklist.ChecklistType.IN_PROCESS,
            "product_line": "Assembly Line A",
            "items": [
                {
                    "sequence": 1,
                    "characteristic": "Torque check",
                    "measurement_type": InspectionItem.MeasurementType.MEASUREMENT,
                    "nominal_value": 25.0,
                    "upper_spec_limit": 27.0,
                    "lower_spec_limit": 23.0,
                    "unit_of_measure": "Nm",
                    "is_critical": True,
                },
                {
                    "sequence": 2,
                    "characteristic": "Label verification",
                    "measurement_type": InspectionItem.MeasurementType.PASS_FAIL,
                    "is_critical": False,
                },
            ],
        }
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        checklist = InspectionChecklist.objects.get(code="CL-NEW-001")
        self.assertEqual(checklist.items.count(), 2)
        self.assertEqual(checklist.created_by, self.user)

    def test_duplicate_checklist(self):
        checklist = InspectionChecklist.objects.create(
            name="Original Checklist",
            code="CL-ORIG-001",
            checklist_type=InspectionChecklist.ChecklistType.FINAL,
            revision="1.0",
            created_by=self.user,
        )
        InspectionItem.objects.create(
            checklist=checklist,
            sequence=1,
            characteristic="Check 1",
            measurement_type=InspectionItem.MeasurementType.PASS_FAIL,
        )
        url = reverse("checklist-duplicate", args=[str(checklist.id)])
        response = self.client.post(url)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn("COPY", response.data["code"])
        self.assertEqual(response.data["revision"], "1.1")
