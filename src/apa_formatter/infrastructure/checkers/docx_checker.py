"""DOCX compliance checker — implements ComplianceCheckerPort.

Wraps the existing validators/checker.py logic, adapting its results
to the domain ComplianceReport format.
"""

from __future__ import annotations

from pathlib import Path

from apa_formatter.domain.ports.compliance_checker import (
    ComplianceCheckerPort,
    ComplianceIssue,
    ComplianceReport,
)


class DocxComplianceChecker(ComplianceCheckerPort):
    """Check .docx files for APA 7 compliance.

    Delegates to the existing APAChecker and maps results to
    domain-level ComplianceReport/ComplianceIssue.
    """

    def check(self, file_path: Path) -> ComplianceReport:
        """Run all compliance checks and return a domain report."""
        from apa_formatter.validators.checker import APAChecker

        checker = APAChecker(file_path)
        legacy_report = checker.check()

        issues: list[ComplianceIssue] = []
        for result in legacy_report.results:
            if not result.passed:
                issues.append(
                    ComplianceIssue(
                        rule=result.rule,
                        message=f"Expected: {result.expected}; Actual: {result.actual}",
                        severity=result.severity,
                    )
                )

        return ComplianceReport(file_path=file_path, issues=issues)
