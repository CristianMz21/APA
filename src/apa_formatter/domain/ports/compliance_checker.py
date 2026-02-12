"""Port: Compliance checker — validate existing documents against APA rules."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class ComplianceIssue:
    """A single compliance finding."""

    rule: str
    message: str
    severity: str = "warning"  # "error" | "warning" | "info"


@dataclass
class ComplianceReport:
    """Aggregated results of a compliance check."""

    file_path: Path
    issues: list[ComplianceIssue] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        """True if no errors were found."""
        return not any(i.severity == "error" for i in self.issues)


class ComplianceCheckerPort(ABC):
    """Contract for checking document compliance against APA 7 rules."""

    @abstractmethod
    def check(self, file_path: Path) -> ComplianceReport:
        """Run compliance checks on the given file and return a report."""
        ...
