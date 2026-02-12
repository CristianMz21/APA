"""Rich formatting utilities for the CLI.

Extracts all Rich rendering (tables, panels, syntax) from the monolithic
cli.py into a dedicated module that knows nothing about domain logic.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax
from rich.table import Table

if TYPE_CHECKING:
    from apa_formatter.domain.ports.compliance_checker import ComplianceReport

console = Console()


# ---------------------------------------------------------------------------
# Success / error panels
# ---------------------------------------------------------------------------


def success_panel(message: str, title: str = "APA Formatter") -> None:
    """Print a green success panel."""
    console.print(Panel(message, title=title, border_style="green"))


def error_message(message: str) -> None:
    """Print a red error message."""
    console.print(f"[bold red]❌ {message}[/]")


# ---------------------------------------------------------------------------
# JSON / config rendering
# ---------------------------------------------------------------------------


def json_panel(raw_json: str, title: str = "⚙️  Configuración APA 7 Activa") -> None:
    """Render JSON inside a syntax-highlighted panel."""
    console.print(
        Panel(
            Syntax(raw_json, "json", theme="monokai", line_numbers=True),
            title=title,
            border_style="blue",
        )
    )


# ---------------------------------------------------------------------------
# APA rules info table
# ---------------------------------------------------------------------------


def rules_table(font_specs: dict, heading_styles: dict) -> None:
    """Print the APA 7 rules information table."""
    table = Table(
        title="📐 Reglas APA 7ª Edición Implementadas",
        show_header=True,
        border_style="blue",
    )
    table.add_column("Regla", style="cyan", width=25)
    table.add_column("Valor", style="green")

    table.add_row("Márgenes", "1 pulgada (2.54 cm) — todos los lados")
    table.add_row("Papel", "Carta (8.5 × 11 pulgadas)")
    table.add_row("Interlineado", "Doble espacio")
    table.add_row("Sangría 1ª línea", "0.5 pulgadas (1.27 cm)")
    table.add_row("Sangría francesa", "0.5 pulgadas (refs)")
    table.add_row("", "")

    for _choice, spec in font_specs.items():
        table.add_row(f"Fuente: {spec.name}", f"{spec.size_pt}pt")

    table.add_row("", "")
    for level, style in heading_styles.items():
        desc_parts = []
        if style.centered:
            desc_parts.append("Centrado")
        else:
            desc_parts.append("Izquierda")
        if style.bold:
            desc_parts.append("Negrita")
        if style.italic:
            desc_parts.append("Cursiva")
        if style.inline:
            desc_parts.append("En línea")
        if style.indent:
            desc_parts.append("Indentado")
        table.add_row(f"Encabezado Nivel {level}", ", ".join(desc_parts))

    console.print(table)


# ---------------------------------------------------------------------------
# Compliance report rendering
# ---------------------------------------------------------------------------


def compliance_table(report: ComplianceReport) -> None:
    """Print a Rich compliance report table plus summary panel."""
    table = Table(
        title="📋 Informe de Cumplimiento APA 7",
        show_header=True,
        border_style="blue",
    )
    table.add_column("", width=3)
    table.add_column("Regla", style="cyan", width=30)
    table.add_column("Esperado", width=30)
    table.add_column("Actual", width=30)

    for r in report.results:
        style = "green" if r.passed else ("red" if r.severity == "error" else "yellow")
        table.add_row(r.icon, f"[{style}]{r.rule}[/]", r.expected, r.actual)

    console.print(table)

    score_color = "green" if report.score >= 80 else "yellow" if report.score >= 60 else "red"
    status = "✅ CUMPLE" if report.is_compliant else "❌ NO CUMPLE"

    console.print(
        Panel(
            f"Resultado: [bold {score_color}]{status}[/]\n"
            f"Puntuación: [bold {score_color}]{report.score:.0f}%[/] "
            f"({report.passed}/{report.total} reglas)\n"
            f"  ✅ Aprobadas: {report.passed}  |  ❌ Fallidas: {report.failed}",
            title="📊 Resumen",
            border_style=score_color,
        )
    )
