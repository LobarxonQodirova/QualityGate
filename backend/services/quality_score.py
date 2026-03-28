"""
Quality Score Service.

Calculates composite quality scores for products, production lines, and
suppliers based on inspection results, defect data, and CAPA effectiveness.
Used by the metrics dashboard and management review reports.
"""

import logging
from dataclasses import dataclass
from datetime import timedelta
from decimal import Decimal
from typing import Optional

from django.db.models import Avg, Count, F, Q, Sum
from django.utils import timezone

logger = logging.getLogger(__name__)


@dataclass
class QualityScoreResult:
    """Structured quality score result."""

    overall_score: float
    inspection_score: float
    defect_score: float
    capa_score: float
    compliance_score: float
    grade: str
    period_start: str
    period_end: str
    details: dict


class QualityScoreService:
    """
    Calculates quality scores on a 0-100 scale.

    The overall score is a weighted average:
      - Inspection pass rate:    35%
      - Defect rate (inverse):   30%
      - CAPA effectiveness:      20%
      - Compliance rate:         15%
    """

    WEIGHTS = {
        "inspection": Decimal("0.35"),
        "defect": Decimal("0.30"),
        "capa": Decimal("0.20"),
        "compliance": Decimal("0.15"),
    }

    GRADE_THRESHOLDS = [
        (95, "A+"),
        (90, "A"),
        (85, "B+"),
        (80, "B"),
        (75, "C+"),
        (70, "C"),
        (60, "D"),
        (0, "F"),
    ]

    def calculate(
        self,
        days: int = 30,
        product_name: Optional[str] = None,
        production_line: Optional[str] = None,
    ) -> QualityScoreResult:
        """
        Calculate a composite quality score for the given period and filters.

        Args:
            days: Number of days to look back.
            product_name: Optional filter by product name.
            production_line: Optional filter by production line.

        Returns:
            QualityScoreResult with component and overall scores.
        """
        end_date = timezone.now()
        start_date = end_date - timedelta(days=days)

        inspection_score = self._inspection_score(start_date, end_date, product_name, production_line)
        defect_score = self._defect_score(start_date, end_date, product_name, production_line)
        capa_score = self._capa_effectiveness_score(start_date, end_date)
        compliance_score = self._compliance_score()

        overall = float(
            Decimal(str(inspection_score)) * self.WEIGHTS["inspection"]
            + Decimal(str(defect_score)) * self.WEIGHTS["defect"]
            + Decimal(str(capa_score)) * self.WEIGHTS["capa"]
            + Decimal(str(compliance_score)) * self.WEIGHTS["compliance"]
        )
        overall = round(overall, 1)
        grade = self._determine_grade(overall)

        logger.info(
            "Quality score calculated: %.1f (%s) for period %s to %s",
            overall, grade, start_date.date(), end_date.date(),
        )

        return QualityScoreResult(
            overall_score=overall,
            inspection_score=round(inspection_score, 1),
            defect_score=round(defect_score, 1),
            capa_score=round(capa_score, 1),
            compliance_score=round(compliance_score, 1),
            grade=grade,
            period_start=start_date.date().isoformat(),
            period_end=end_date.date().isoformat(),
            details={
                "weights": {k: float(v) for k, v in self.WEIGHTS.items()},
                "days": days,
                "product_name": product_name,
                "production_line": production_line,
            },
        )

    def _inspection_score(self, start, end, product_name, production_line):
        """Score based on inspection pass rate (0-100)."""
        from apps.inspections.models import Inspection

        qs = Inspection.objects.filter(
            status=Inspection.Status.COMPLETED,
            completed_at__range=(start, end),
        )
        if product_name:
            qs = qs.filter(product_name__icontains=product_name)
        if production_line:
            qs = qs.filter(production_line__icontains=production_line)

        total = qs.count()
        if total == 0:
            return 100.0  # No inspections means no failures

        accepted = qs.filter(disposition=Inspection.Disposition.ACCEPT).count()
        return (accepted / total) * 100

    def _defect_score(self, start, end, product_name, production_line):
        """Score inversely proportional to defect rate (0-100)."""
        from apps.defects.models import Defect
        from apps.inspections.models import Inspection

        defect_qs = Defect.objects.filter(detected_date__range=(start, end))
        insp_qs = Inspection.objects.filter(
            status=Inspection.Status.COMPLETED,
            completed_at__range=(start, end),
        )
        if product_name:
            defect_qs = defect_qs.filter(product_name__icontains=product_name)
            insp_qs = insp_qs.filter(product_name__icontains=product_name)
        if production_line:
            defect_qs = defect_qs.filter(production_line__icontains=production_line)
            insp_qs = insp_qs.filter(production_line__icontains=production_line)

        defect_count = defect_qs.count()
        total_inspected = insp_qs.aggregate(s=Sum("sample_size"))["s"] or 0

        if total_inspected == 0:
            return 100.0

        defect_rate = defect_count / total_inspected
        # Scale: 0% defects = 100 score, 10%+ defects = 0 score
        score = max(0, (1 - defect_rate / 0.10)) * 100
        return min(score, 100.0)

    def _capa_effectiveness_score(self, start, end):
        """Score based on CAPA verification effectiveness (0-100)."""
        from apps.capa.models import CorrectiveAction

        verified = CorrectiveAction.objects.filter(
            verification_date__range=(start, end),
            status__in=[
                CorrectiveAction.Status.VERIFIED_EFFECTIVE,
                CorrectiveAction.Status.VERIFIED_INEFFECTIVE,
            ],
        )
        total = verified.count()
        if total == 0:
            return 100.0  # No CAPAs verified means nothing failed

        effective = verified.filter(
            status=CorrectiveAction.Status.VERIFIED_EFFECTIVE,
        ).count()
        avg_rating = verified.filter(
            effectiveness_rating__isnull=False,
        ).aggregate(avg=Avg("effectiveness_rating"))["avg"] or 0

        # Blend verification pass rate (60%) with average effectiveness rating (40%)
        pass_rate_score = (effective / total) * 100
        rating_score = (avg_rating / 5) * 100
        return pass_rate_score * 0.6 + rating_score * 0.4

    def _compliance_score(self):
        """Score based on overall compliance assessment status (0-100)."""
        from apps.compliance.models import ComplianceAssessment, ComplianceRequirement

        applicable = ComplianceRequirement.objects.filter(is_applicable=True)
        total = applicable.count()
        if total == 0:
            return 100.0

        compliant = 0
        partial = 0
        for req in applicable:
            latest = req.latest_assessment
            if latest:
                if latest.status == ComplianceAssessment.Status.COMPLIANT:
                    compliant += 1
                elif latest.status == ComplianceAssessment.Status.PARTIALLY_COMPLIANT:
                    partial += 1

        # Fully compliant = full credit, partially = half credit
        score = ((compliant + partial * 0.5) / total) * 100
        return min(score, 100.0)

    def _determine_grade(self, score: float) -> str:
        """Map a numeric score to a letter grade."""
        for threshold, grade in self.GRADE_THRESHOLDS:
            if score >= threshold:
                return grade
        return "F"
