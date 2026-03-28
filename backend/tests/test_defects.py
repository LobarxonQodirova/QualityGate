"""
Tests for the defects app.
Covers models, serializers, views, and business logic.
"""

from datetime import timedelta

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient, APITestCase

from apps.accounts.models import User
from apps.defects.models import Defect, DefectCategory, DefectImage, RootCauseAnalysis


class DefectCategoryModelTest(TestCase):
    """Tests for DefectCategory model."""

    def setUp(self):
        self.parent = DefectCategory.objects.create(
            name="Dimensional",
            code="DIM",
        )
        self.child = DefectCategory.objects.create(
            name="Out of Tolerance",
            code="DIM-OOT",
            parent=self.parent,
        )

    def test_str_representation(self):
        self.assertEqual(str(self.parent), "DIM - Dimensional")

    def test_parent_child_relationship(self):
        self.assertEqual(self.child.parent, self.parent)
        self.assertIn(self.child, self.parent.subcategories.all())


class DefectModelTest(TestCase):
    """Tests for Defect model."""

    def setUp(self):
        self.reporter = User.objects.create_user(
            username="reporter",
            email="reporter@example.com",
            password="TestPass1234!",
            first_name="Reporter",
            last_name="User",
            role=User.Role.INSPECTOR,
        )
        self.category = DefectCategory.objects.create(
            name="Surface",
            code="SUR",
        )

    def test_auto_number_generation(self):
        defect = Defect.objects.create(
            title="Scratch on surface",
            description="Visible scratch on front panel",
            category=self.category,
            severity=Defect.Severity.MINOR,
            product_name="Panel A",
            reported_by=self.reporter,
        )
        self.assertTrue(defect.defect_number.startswith("DEF-"))
        parts = defect.defect_number.split("-")
        self.assertEqual(len(parts), 3)

    def test_sequential_numbering(self):
        d1 = Defect.objects.create(
            title="Defect 1",
            description="First defect",
            product_name="Product X",
            reported_by=self.reporter,
        )
        d2 = Defect.objects.create(
            title="Defect 2",
            description="Second defect",
            product_name="Product X",
            reported_by=self.reporter,
        )
        seq1 = int(d1.defect_number.split("-")[-1])
        seq2 = int(d2.defect_number.split("-")[-1])
        self.assertEqual(seq2, seq1 + 1)

    def test_defect_rate_calculation(self):
        defect = Defect.objects.create(
            title="Rate test",
            description="Testing defect rate",
            product_name="Product Y",
            quantity_affected=5,
            quantity_inspected=100,
            reported_by=self.reporter,
        )
        self.assertEqual(defect.defect_rate, 5.0)

    def test_defect_rate_zero_inspected(self):
        defect = Defect.objects.create(
            title="Zero inspected",
            description="Edge case",
            product_name="Product Z",
            quantity_affected=1,
            quantity_inspected=0,
            reported_by=self.reporter,
        )
        self.assertEqual(defect.defect_rate, 0)

    def test_is_overdue(self):
        defect = Defect.objects.create(
            title="Overdue defect",
            description="Should be overdue",
            product_name="Product A",
            target_close_date=timezone.now().date() - timedelta(days=5),
            reported_by=self.reporter,
        )
        self.assertTrue(defect.is_overdue)

    def test_not_overdue_when_closed(self):
        defect = Defect.objects.create(
            title="Closed defect",
            description="Not overdue because closed",
            product_name="Product B",
            status=Defect.Status.CLOSED,
            target_close_date=timezone.now().date() - timedelta(days=5),
            closed_date=timezone.now(),
            reported_by=self.reporter,
        )
        self.assertFalse(defect.is_overdue)

    def test_days_open(self):
        detected = timezone.now() - timedelta(days=10)
        defect = Defect.objects.create(
            title="Open defect",
            description="Open for 10 days",
            product_name="Product C",
            detected_date=detected,
            reported_by=self.reporter,
        )
        self.assertAlmostEqual(defect.days_open, 10, delta=1)


class RootCauseAnalysisModelTest(TestCase):
    """Tests for RootCauseAnalysis model."""

    def setUp(self):
        self.user = User.objects.create_user(
            username="analyst",
            email="analyst@example.com",
            password="TestPass1234!",
            role=User.Role.QUALITY_ENGINEER,
        )
        self.defect = Defect.objects.create(
            title="RCA test defect",
            description="Defect for RCA testing",
            product_name="Component X",
            reported_by=self.user,
        )

    def test_five_why_analysis(self):
        rca = RootCauseAnalysis.objects.create(
            defect=self.defect,
            methodology=RootCauseAnalysis.Methodology.FIVE_WHY,
            why_1="Machine stopped unexpectedly",
            why_2="Overheating caused shutdown",
            why_3="Cooling system failed",
            why_4="Coolant pump seal was leaking",
            why_5="Preventive maintenance was overdue",
            root_cause="Preventive maintenance schedule not followed",
            cause_category=RootCauseAnalysis.CauseCategory.METHOD,
            analyzed_by=self.user,
        )
        self.assertEqual(rca.methodology, "five_why")
        self.assertIn("maintenance", rca.root_cause)
        self.assertFalse(rca.is_verified)

    def test_str_representation(self):
        rca = RootCauseAnalysis.objects.create(
            defect=self.defect,
            methodology=RootCauseAnalysis.Methodology.FISHBONE,
            root_cause="Incorrect tooling setup caused dimensional deviation",
            analyzed_by=self.user,
        )
        self.assertIn("RCA for", str(rca))
        self.assertIn(self.defect.defect_number, str(rca))


class DefectAPITest(APITestCase):
    """Tests for defect API endpoints."""

    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username="defect_api_user",
            email="defectapi@example.com",
            password="TestPass1234!",
            first_name="Defect",
            last_name="Tester",
            role=User.Role.QUALITY_ENGINEER,
        )
        self.client.force_authenticate(user=self.user)

        self.category = DefectCategory.objects.create(
            name="Functional",
            code="FUNC",
        )

    def test_create_defect(self):
        url = reverse("defect-list")
        data = {
            "title": "Motor does not start",
            "description": "Unit fails to power on when switch is activated",
            "category": str(self.category.id),
            "severity": Defect.Severity.MAJOR,
            "detection_method": Defect.DetectionMethod.TESTING,
            "product_name": "Motor Assembly X200",
            "part_number": "MA-X200-01",
            "batch_number": "BATCH-2026-01",
            "quantity_affected": 3,
            "quantity_inspected": 50,
            "target_close_date": (timezone.now().date() + timedelta(days=14)).isoformat(),
        }
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn("id", response.data)

        defect = Defect.objects.get(id=response.data["id"])
        self.assertEqual(defect.reported_by, self.user)
        self.assertEqual(defect.severity, Defect.Severity.MAJOR)

    def test_list_defects_with_search(self):
        Defect.objects.create(
            title="Crack in housing",
            description="Visible crack",
            product_name="Housing Part",
            reported_by=self.user,
        )
        Defect.objects.create(
            title="Color mismatch",
            description="Wrong color applied",
            product_name="Cover Panel",
            reported_by=self.user,
        )
        url = reverse("defect-list")
        response = self.client.get(url, {"search": "crack"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data.get("results", response.data)
        matching = [d for d in results if "crack" in d["title"].lower()]
        self.assertGreaterEqual(len(matching), 1)

    def test_close_defect(self):
        defect = Defect.objects.create(
            title="Closeable defect",
            description="Ready to close",
            product_name="Widget",
            status=Defect.Status.VERIFICATION,
            reported_by=self.user,
        )
        url = reverse("defect-close-defect", args=[str(defect.id)])
        response = self.client.post(url, {"actual_cost": "150.00"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        defect.refresh_from_db()
        self.assertEqual(defect.status, Defect.Status.CLOSED)
        self.assertIsNotNone(defect.closed_date)
        self.assertEqual(defect.closed_by, self.user)

    def test_close_already_closed_defect_fails(self):
        defect = Defect.objects.create(
            title="Already closed",
            description="Cannot close again",
            product_name="Widget",
            status=Defect.Status.CLOSED,
            closed_date=timezone.now(),
            reported_by=self.user,
        )
        url = reverse("defect-close-defect", args=[str(defect.id)])
        response = self.client.post(url)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_assign_defect(self):
        assignee = User.objects.create_user(
            username="assignee",
            email="assignee@example.com",
            password="TestPass1234!",
            role=User.Role.QUALITY_ENGINEER,
        )
        defect = Defect.objects.create(
            title="Assign me",
            description="Needs assignment",
            product_name="Part",
            status=Defect.Status.OPEN,
            reported_by=self.user,
        )
        url = reverse("defect-assign-defect", args=[str(defect.id)])
        response = self.client.post(
            url, {"assigned_to": str(assignee.id)}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        defect.refresh_from_db()
        self.assertEqual(defect.assigned_to, assignee)
        self.assertEqual(defect.status, Defect.Status.UNDER_REVIEW)

    def test_summary_endpoint(self):
        Defect.objects.create(
            title="Summary defect 1",
            description="For summary",
            product_name="Part",
            severity=Defect.Severity.CRITICAL,
            reported_by=self.user,
        )
        Defect.objects.create(
            title="Summary defect 2",
            description="For summary",
            product_name="Part",
            severity=Defect.Severity.MINOR,
            status=Defect.Status.CLOSED,
            closed_date=timezone.now(),
            reported_by=self.user,
        )
        url = reverse("defect-summary")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("total", response.data)
        self.assertIn("open", response.data)
        self.assertIn("by_severity", response.data)
        self.assertGreaterEqual(response.data["total"], 2)


class RootCauseAnalysisAPITest(APITestCase):
    """Tests for RCA API endpoints."""

    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username="rca_user",
            email="rca@example.com",
            password="TestPass1234!",
            role=User.Role.QUALITY_ENGINEER,
        )
        self.client.force_authenticate(user=self.user)

        self.defect = Defect.objects.create(
            title="RCA defect",
            description="Needs root cause analysis",
            product_name="Assembly",
            reported_by=self.user,
        )

    def test_create_rca(self):
        url = reverse("root-cause-analysis-list")
        data = {
            "defect": str(self.defect.id),
            "methodology": RootCauseAnalysis.Methodology.FIVE_WHY,
            "why_1": "Part failed during testing",
            "why_2": "Material was below specification",
            "why_3": "Incoming inspection missed the defect",
            "why_4": "Checklist did not include this parameter",
            "why_5": "Checklist review process was not followed",
            "root_cause": "Inadequate incoming inspection checklist",
            "cause_category": RootCauseAnalysis.CauseCategory.METHOD,
        }
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        rca = RootCauseAnalysis.objects.get(defect=self.defect)
        self.assertEqual(rca.analyzed_by, self.user)

    def test_verify_rca(self):
        rca = RootCauseAnalysis.objects.create(
            defect=self.defect,
            methodology=RootCauseAnalysis.Methodology.FISHBONE,
            root_cause="Material issue",
            analyzed_by=self.user,
        )
        url = reverse("root-cause-analysis-verify", args=[str(rca.id)])
        response = self.client.post(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        rca.refresh_from_db()
        self.assertTrue(rca.is_verified)
        self.assertEqual(rca.verified_by, self.user)
        self.assertIsNotNone(rca.verified_date)
