"""
Account models: User, QualityTeam, Inspector.
"""

import uuid

from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """Extended user model with quality-specific fields."""

    class Role(models.TextChoices):
        ADMIN = "admin", "Administrator"
        QUALITY_MANAGER = "quality_manager", "Quality Manager"
        QUALITY_ENGINEER = "quality_engineer", "Quality Engineer"
        INSPECTOR = "inspector", "Inspector"
        AUDITOR = "auditor", "Auditor"
        OPERATOR = "operator", "Operator"
        VIEWER = "viewer", "Viewer"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(unique=True)
    role = models.CharField(max_length=30, choices=Role.choices, default=Role.VIEWER)
    employee_id = models.CharField(max_length=50, unique=True, blank=True, null=True)
    department = models.CharField(max_length=100, blank=True)
    phone = models.CharField(max_length=30, blank=True)
    avatar = models.ImageField(upload_to="avatars/", blank=True, null=True)
    is_certified_inspector = models.BooleanField(default=False)
    certification_expiry = models.DateField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["username", "first_name", "last_name"]

    class Meta:
        ordering = ["last_name", "first_name"]
        verbose_name = "User"
        verbose_name_plural = "Users"

    def __str__(self):
        return f"{self.get_full_name()} ({self.employee_id or self.email})"

    @property
    def full_name(self):
        return self.get_full_name() or self.email

    @property
    def is_quality_staff(self):
        return self.role in (
            self.Role.ADMIN,
            self.Role.QUALITY_MANAGER,
            self.Role.QUALITY_ENGINEER,
            self.Role.INSPECTOR,
            self.Role.AUDITOR,
        )


class QualityTeam(models.Model):
    """A team of quality personnel assigned to a production area or product line."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    leader = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="led_teams",
    )
    members = models.ManyToManyField(User, related_name="quality_teams", blank=True)
    production_area = models.CharField(max_length=200, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]
        verbose_name = "Quality Team"
        verbose_name_plural = "Quality Teams"

    def __str__(self):
        return self.name

    @property
    def member_count(self):
        return self.members.count()


class Inspector(models.Model):
    """Inspector profile with certification and qualification tracking."""

    class CertificationLevel(models.TextChoices):
        LEVEL_1 = "level_1", "Level 1 - Basic"
        LEVEL_2 = "level_2", "Level 2 - Intermediate"
        LEVEL_3 = "level_3", "Level 3 - Advanced"
        LEAD = "lead", "Lead Inspector"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="inspector_profile")
    certification_level = models.CharField(
        max_length=20,
        choices=CertificationLevel.choices,
        default=CertificationLevel.LEVEL_1,
    )
    certification_number = models.CharField(max_length=100, blank=True)
    certified_date = models.DateField(blank=True, null=True)
    certification_expiry = models.DateField(blank=True, null=True)
    specializations = models.JSONField(
        default=list,
        blank=True,
        help_text="List of inspection specializations (e.g., ['dimensional', 'visual', 'NDT'])",
    )
    qualified_standards = models.JSONField(
        default=list,
        blank=True,
        help_text="List of standards the inspector is qualified for (e.g., ['ISO 9001', 'AS9100'])",
    )
    total_inspections = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-certification_level", "user__last_name"]
        verbose_name = "Inspector"
        verbose_name_plural = "Inspectors"

    def __str__(self):
        return f"{self.user.full_name} - {self.get_certification_level_display()}"

    @property
    def is_certification_valid(self):
        if not self.certification_expiry:
            return False
        from django.utils import timezone
        return self.certification_expiry >= timezone.now().date()
