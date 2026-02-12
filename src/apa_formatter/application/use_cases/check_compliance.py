"""Use Case: Check Document Compliance.

Delegates compliance checking to an injected ComplianceCheckerPort.
"""

from pathlib import Path

from apa_formatter.domain.ports.compliance_checker import (
    ComplianceCheckerPort,
    ComplianceReport,
)


class CheckComplianceUseCase:
    """Orchestrate document compliance checking."""

    def __init__(self, checker: ComplianceCheckerPort) -> None:
        self._checker = checker

    def execute(self, file_path: Path) -> ComplianceReport:
        """Run compliance checks on the given file.

        Args:
            file_path: Path to the document to check.

        Returns:
            A ComplianceReport with all findings.
        """
        return self._checker.check(file_path)
