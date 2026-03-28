"""
Tests for the CAPA app.
Covers corrective actions, preventive actions, tasks, and workflow.
"""

from datetime import timedelta

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient, APITestCase

from apps.accounts.models import User
from apps.capa.models import CAPATask, CorrectiveAction, PreventiveAction
from apps.defects.models import Defect


class CorrectiveActionModelTest(TestCase):
    """Tests for CorrectiveAction model."""

    def setUp(self):
        self.user = User.objects.create_user(
            username="ca_user",
            email="ca@example.com",
            password="TestPass1234!",
            role=User.Role.QUALITY_ENGINEER,
        )

    def test_auto_number_generation(self):
        ca = CorrectiveAction.objects.create(
            title="Fix welding defects",
            description="Address root cause of weld porosity",
            action_plan="Retrain operators and recalibrate welding equipment",
            target_date=timezone.now().date() + timedelta(days=30),
            initiated_by=self.user,
        )
        self.assertTrue(ca.ca_number.startswith("CA-"))
        self.assertEqual(len(ca.ca_number.split("-")), 3)

    def test_is_overdue(self):
        ca = CorrectiveAction.objects.create(
            title="Overdue CA",
            description="Past target date",
            action_plan="Action plan",
            target_date=timezone.now().date() - timedelta(days=5),
            status=CorrectiveAction.Status.IN_PROGRESS,
            initiated_by=self.user,
        )
        self.assertTrue(ca.is_overdue)

    def test_not_overdue_when_closed(self):
        ca = CorrectiveAction.objects.create(
            title="Closed CA",
            description="Completed on time",
            action_plan="Action plan",
            target_date=timezone.now().date() - timedelta(days=5),
            status=CorrectiveAction.Status.CLOSED,
            initiated_by=self.user,
        )
        self.assertFalse(ca.is_overdue)

    def test_task_completion_rate(self):
        ca = CorrectiveAction.objects.create(
            title="CA with tasks",
            description="Multiple tasks",
            action_plan="Step-by-step plan",
            target_date=timezone.now().date() + timedelta(days=30),
            initiated_by=self.user,
        )
        CAPATask.objects.create(
            corrective_action=ca,
            sequence=1,
            title="Task 1",
            status=CAPATask.Status.COMPLETED,
            due_date=timezone.now().date(),
            completed_date=timezone.now(),
        )
        CAPATask.objects.create(
            corrective_action=ca,
            sequence=2,
            title="Task 2",
            status=CAPATask.Status.IN_PROGRESS,
            due_date=timezone.now().date() + timedelta(days=7),
        )
        self.assertEqual(ca.task_completion_rate, 50.0)

    def test_task_completion_rate_no_tasks(self):
        ca = CorrectiveAction.objects.create(
            title="CA no tasks",
            description="No tasks yet",
            action_plan="TBD",
            target_date=timezone.now().date() + timedelta(days=30),
            initiated_by=self.user,
        )
        self.assertIsNone(ca.task_completion_rate)


class CAPATaskModelTest(TestCase):
    """Tests for CAPATask model."""

    def setUp(self):
        self.user = User.objects.create_user(
            username="task_user",
            email="task@example.com",
            password="TestPass1234!",
            role=User.Role.QUALITY_ENGINEER,
        )
        self.ca = CorrectiveAction.objects.create(
            title="Parent CA",
            description="Parent for tasks",
            action_plan="Plan",
            target_date=timezone.now().date() + timedelta(days=30),
            initiated_by=self.user,
        )

    def test_task_is_overdue(self):
        task = CAPATask.objects.create(
            corrective_action=self.ca,
            sequence=1,
            title="Overdue task",
            due_date=timezone.now().date() - timedelta(days=3),
            status=CAPATask.Status.IN_PROGRESS,
        )
        self.assertTrue(task.is_overdue)

    def test_completed_task_not_overdue(self):
        task = CAPATask.objects.create(
            corrective_action=self.ca,
            sequence=1,
            title="Done task",
            due_date=timezone.now().date() - timedelta(days=3),
            status=CAPATask.Status.COMPLETED,
            completed_date=timezone.now(),
        )
        self.assertFalse(task.is_overdue)

    def test_str_representation(self):
        task = CAPATask.objects.create(
            corrective_action=self.ca,
            sequence=1,
            title="Retrain operators",
            due_date=timezone.now().date() + timedelta(days=7),
        )
        self.assertIn("Task #1", str(task))
        self.assertIn("Retrain operators", str(task))


class CorrectiveActionAPITest(APITestCase):
    """Tests for corrective action API endpoints."""

    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username="ca_api_user",
            email="caapi@example.com",
            password="TestPass1234!",
            first_name="CA",
            last_name="Tester",
            role=User.Role.QUALITY_MANAGER,
        )
        self.client.force_authenticate(user=self.user)

    def test_create_corrective_action_with_tasks(self):
        url = reverse("corrective-action-list")
        data = {
            "title": "Address weld porosity",
            "description": "Multiple weld defects reported in batch B-2026-03",
            "source": CorrectiveAction.Source.DEFECT,
            "priority": CorrectiveAction.Priority.HIGH,
            "action_plan": "1. Retrain welders\n2. Recalibrate equipment\n3. Verify with test welds",
            "root_cause": "Incorrect gas flow rate settings",
            "target_date": (timezone.now().date() + timedelta(days=21)).isoformat(),
            "tasks": [
                {
                    "title": "Retrain welding operators",
                    "due_date": (timezone.now().date() + timedelta(days=7)).isoformat(),
                },
                {
                    "title": "Recalibrate MIG equipment",
                    "due_date": (timezone.now().date() + timedelta(days=10)).isoformat(),
                },
            ],
        }
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        ca = CorrectiveAction.objects.get(id=response.data["id"])
        self.assertEqual(ca.initiated_by, self.user)
        self.assertEqual(ca.tasks.count(), 2)

    def test_verify_corrective_action_effective(self):
        ca = CorrectiveAction.objects.create(
            title="CA to verify",
            description="Needs verification",
            action_plan="Completed actions",
            target_date=timezone.now().date(),
            status=CorrectiveAction.Status.PENDING_VERIFICATION,
            initiated_by=self.user,
        )
        url = reverse("corrective-action-verify", args=[str(ca.id)])
        response = self.client.post(url, {
            "effectiveness_rating": 5,
            "verification_results": "All test welds passed inspection",
            "verification_method": "Re-inspection of 50 samples",
        }, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        ca.refresh_from_db()
        self.assertEqual(ca.status, CorrectiveAction.Status.VERIFIED_EFFECTIVE)
        self.assertEqual(ca.effectiveness_rating, 5)
        self.assertEqual(ca.verified_by, self.user)

    def test_verify_corrective_action_ineffective(self):
        ca = CorrectiveAction.objects.create(
            title="Ineffective CA",
            description="Did not work",
            action_plan="Plan",
            target_date=timezone.now().date(),
            status=CorrectiveAction.Status.PENDING_VERIFICATION,
            initiated_by=self.user,
        )
        url = reverse("corrective-action-verify", args=[str(ca.id)])
        response = self.client.post(url, {
            "effectiveness_rating": 2,
            "verification_results": "Defects still recurring",
        }, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        ca.refresh_from_db()
        self.assertEqual(ca.status, CorrectiveAction.Status.VERIFIED_INEFFECTIVE)

    def test_close_requires_verified_effective(self):
        ca = CorrectiveAction.objects.create(
            title="Cannot close yet",
            description="Not verified",
            action_plan="Plan",
            target_date=timezone.now().date(),
            status=CorrectiveAction.Status.IN_PROGRESS,
            initiated_by=self.user,
        )
        url = reverse("corrective-action-close", args=[str(ca.id)])
        response = self.client.post(url)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_close_verified_ca(self):
        ca = CorrectiveAction.objects.create(
            title="Close me",
            description="Verified effective",
            action_plan="Plan",
            target_date=timezone.now().date(),
            status=CorrectiveAction.Status.VERIFIED_EFFECTIVE,
            initiated_by=self.user,
        )
        url = reverse("corrective-action-close", args=[str(ca.id)])
        response = self.client.post(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        ca.refresh_from_db()
        self.assertEqual(ca.status, CorrectiveAction.Status.CLOSED)
        self.assertIsNotNone(ca.completed_date)

    def test_summary_endpoint(self):
        CorrectiveAction.objects.create(
            title="Open CA",
            description="Open",
            action_plan="Plan",
            target_date=timezone.now().date() + timedelta(days=30),
            status=CorrectiveAction.Status.OPEN,
            initiated_by=self.user,
        )
        url = reverse("corrective-action-summary")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("total", response.data)
        self.assertIn("open", response.data)
        self.assertIn("overdue", response.data)

    def test_complete_task(self):
        ca = CorrectiveAction.objects.create(
            title="CA with task",
            description="Test task completion",
            action_plan="Plan",
            target_date=timezone.now().date() + timedelta(days=30),
            initiated_by=self.user,
        )
        task = CAPATask.objects.create(
            corrective_action=ca,
            sequence=1,
            title="Task to complete",
            due_date=timezone.now().date() + timedelta(days=7),
        )
        url = reverse("capa-task-complete-task", args=[str(task.id)])
        response = self.client.post(url, {
            "completion_notes": "Task completed successfully",
        }, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        task.refresh_from_db()
        self.assertEqual(task.status, CAPATask.Status.COMPLETED)
        self.assertIsNotNone(task.completed_date)
