"""CLI interface for APA 7 Document Formatter."""

from __future__ import annotations

import shutil
from datetime import date
from pathlib import Path
from typing import Annotated, Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax
from rich.table import Table

from apa_formatter.config import APAConfig, get_config, load_config
from apa_formatter.config.loader import _DEFAULT_CONFIG_PATH
from apa_formatter.models.document import (
    APADocument,
    Author,
    Reference,
    Section,
    TitlePage,
)
from apa_formatter.models.enums import (
    DocumentVariant,
    FontChoice,
    HeadingLevel,
    OutputFormat,
    ReferenceType,
)

app = typer.Typer(
    name="apa",
    help="📄 Formateador de documentos APA 7ª Edición — Word (.docx) y PDF",
    rich_markup_mode="rich",
    no_args_is_help=True,
)

# Sub-app for config commands
config_app = typer.Typer(
    name="config",
    help="⚙️  Gestionar la configuración APA 7",
    rich_markup_mode="rich",
    no_args_is_help=True,
)
app.add_typer(config_app, name="config")

console = Console()


# ---------------------------------------------------------------------------
# apa create
# ---------------------------------------------------------------------------


@app.command()
def create(
    title: Annotated[str, typer.Option("--title", "-t", help="Título del trabajo")],
    author: Annotated[list[str], typer.Option("--author", "-a", help="Nombre(s) del autor")] = None,
    affiliation: Annotated[
        str, typer.Option("--affiliation", help="Afiliación institucional")
    ] = "Universidad",
    course: Annotated[
        Optional[str], typer.Option("--course", help="Número y nombre del curso")
    ] = None,
    instructor: Annotated[
        Optional[str], typer.Option("--instructor", help="Nombre del instructor")
    ] = None,
    abstract: Annotated[
        Optional[str], typer.Option("--abstract", help="Texto del abstract")
    ] = None,
    font: Annotated[
        FontChoice, typer.Option("--font", "-f", help="Fuente a usar")
    ] = FontChoice.TIMES_NEW_ROMAN,
    variant: Annotated[
        DocumentVariant,
        typer.Option("--variant", "-v", help="Tipo de paper (student/professional)"),
    ] = DocumentVariant.STUDENT,
    output: Annotated[
        str, typer.Option("--output", "-o", help="Archivo de salida (.docx o .pdf)")
    ] = "document.docx",
    config: Annotated[
        Optional[str], typer.Option("--config", "-c", help="Ruta a archivo JSON de configuración")
    ] = None,
) -> None:
    """Crear un documento APA 7 con los parámetros especificados."""
    authors = author or ["Autor Desconocido"]
    out_format = OutputFormat.PDF if output.endswith(".pdf") else OutputFormat.DOCX

    title_page = TitlePage(
        title=title,
        authors=authors,
        affiliation=affiliation,
        course=course,
        instructor=instructor,
        due_date=date.today(),
        variant=variant,
    )

    doc = APADocument(
        title_page=title_page,
        abstract=abstract,
        font=font,
        output_format=out_format,
        sections=[
            Section(
                heading="Introduction",
                level=HeadingLevel.LEVEL_1,
                content="[Escriba aquí la introducción de su trabajo.]",
            ),
            Section(
                heading="Method",
                level=HeadingLevel.LEVEL_1,
                content="[Describa la metodología utilizada.]",
                subsections=[
                    Section(
                        heading="Participants",
                        level=HeadingLevel.LEVEL_2,
                        content="[Describa los participantes del estudio.]",
                    ),
                    Section(
                        heading="Procedure",
                        level=HeadingLevel.LEVEL_2,
                        content="[Describa el procedimiento seguido.]",
                    ),
                ],
            ),
            Section(
                heading="Results",
                level=HeadingLevel.LEVEL_1,
                content="[Presente los resultados encontrados.]",
            ),
            Section(
                heading="Discussion",
                level=HeadingLevel.LEVEL_1,
                content="[Discuta los hallazgos y sus implicaciones.]",
            ),
        ],
    )

    cfg = load_config(Path(config)) if config else get_config()
    output_path = _generate_document(doc, Path(output), cfg)
    console.print(
        Panel(
            f"✅ Documento creado: [bold green]{output_path}[/]",
            title="APA Formatter",
            border_style="green",
        )
    )


# ---------------------------------------------------------------------------
# apa demo
# ---------------------------------------------------------------------------


@app.command()
def demo(
    output: Annotated[
        str, typer.Option("--output", "-o", help="Archivo de salida")
    ] = "demo_apa7.docx",
    font: Annotated[
        FontChoice, typer.Option("--font", "-f", help="Fuente")
    ] = FontChoice.TIMES_NEW_ROMAN,
    config: Annotated[
        Optional[str], typer.Option("--config", "-c", help="Ruta a archivo JSON de configuración")
    ] = None,
) -> None:
    """Generar un documento de ejemplo completo con todas las características APA 7."""
    out_format = OutputFormat.PDF if output.endswith(".pdf") else OutputFormat.DOCX

    cfg = load_config(Path(config)) if config else get_config()
    doc = _build_demo_document(font, out_format)
    output_path = _generate_document(doc, Path(output), cfg)

    console.print(
        Panel(
            f"✅ Documento de ejemplo generado: [bold green]{output_path}[/]\n\n"
            "📋 Incluye:\n"
            "  • Página de título APA 7 (estudiante)\n"
            "  • Abstract con palabras clave\n"
            "  • Secciones con 5 niveles de encabezados\n"
            "  • Lista de referencias con sangría francesa\n"
            "  • Apéndice de ejemplo",
            title="🎓 APA 7 Demo",
            border_style="blue",
        )
    )


# ---------------------------------------------------------------------------
# apa convert
# ---------------------------------------------------------------------------


@app.command()
def convert(
    source: Annotated[str, typer.Argument(help="Archivo fuente (.docx)")],
    output: Annotated[
        Optional[str], typer.Option("--output", "-o", help="Archivo de salida")
    ] = None,
) -> None:
    """Convertir un documento .docx a PDF con formato APA 7."""
    from apa_formatter.converters import docx_to_pdf

    source_path = Path(source)
    if not source_path.exists():
        console.print(f"[bold red]❌ Archivo no encontrado:[/] {source}")
        raise typer.Exit(code=1)

    if source_path.suffix.lower() != ".docx":
        console.print("[bold red]❌ Solo se soporta conversión de .docx a .pdf[/]")
        raise typer.Exit(code=1)

    out_path = Path(output) if output else source_path.with_suffix(".pdf")

    try:
        result = docx_to_pdf(source_path, out_path)
        console.print(
            Panel(
                f"✅ Convertido exitosamente:\n"
                f"  📥 Fuente: [cyan]{source_path}[/]\n"
                f"  📤 Salida: [bold green]{result}[/]\n\n"
                f"[dim]Nota: El contenido se re-formatea según APA 7 durante la conversión.[/]",
                title="🔄 APA Convert",
                border_style="green",
            )
        )
    except Exception as e:
        console.print(f"[bold red]❌ Error durante la conversión:[/] {e}")
        raise typer.Exit(code=1)


# ---------------------------------------------------------------------------
# apa check
# ---------------------------------------------------------------------------


@app.command()
def check(
    source: Annotated[str, typer.Argument(help="Archivo .docx a verificar")],
) -> None:
    """Verificar el cumplimiento APA 7 de un documento .docx existente."""
    from apa_formatter.validators.checker import APAChecker

    source_path = Path(source)
    if not source_path.exists():
        console.print(f"[bold red]❌ Archivo no encontrado:[/] {source}")
        raise typer.Exit(code=1)

    try:
        checker = APAChecker(source_path)
        report = checker.check()
    except (FileNotFoundError, ValueError) as e:
        console.print(f"[bold red]❌ Error:[/] {e}")
        raise typer.Exit(code=1)

    # Build results table
    table = Table(title="📋 Informe de Cumplimiento APA 7", show_header=True, border_style="blue")
    table.add_column("", width=3)
    table.add_column("Regla", style="cyan", width=30)
    table.add_column("Esperado", width=30)
    table.add_column("Actual", width=30)

    for r in report.results:
        style = "green" if r.passed else ("red" if r.severity == "error" else "yellow")
        table.add_row(r.icon, f"[{style}]{r.rule}[/]", r.expected, r.actual)

    console.print(table)

    # Summary
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


# ---------------------------------------------------------------------------
# apa info
# ---------------------------------------------------------------------------


@app.command()
def info() -> None:
    """Mostrar las reglas APA 7 implementadas."""
    from apa_formatter.rules.constants import FONT_SPECS, HEADING_STYLES

    table = Table(
        title="📐 Reglas APA 7ª Edición Implementadas", show_header=True, border_style="blue"
    )
    table.add_column("Regla", style="cyan", width=25)
    table.add_column("Valor", style="green")

    table.add_row("Márgenes", "1 pulgada (2.54 cm) — todos los lados")
    table.add_row("Papel", "Carta (8.5 × 11 pulgadas)")
    table.add_row("Interlineado", "Doble espacio")
    table.add_row("Sangría 1ª línea", "0.5 pulgadas (1.27 cm)")
    table.add_row("Sangría francesa", "0.5 pulgadas (refs)")
    table.add_row("", "")

    for choice, spec in FONT_SPECS.items():
        table.add_row(f"Fuente: {spec.name}", f"{spec.size_pt}pt")

    table.add_row("", "")
    for level, style in HEADING_STYLES.items():
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
# apa config show / init
# ---------------------------------------------------------------------------


@config_app.command("show")
def config_show(
    config: Annotated[
        Optional[str], typer.Option("--config", "-c", help="Ruta a archivo JSON de configuración")
    ] = None,
) -> None:
    """Mostrar la configuración APA 7 activa (formateada)."""
    cfg = load_config(Path(config)) if config else get_config()
    raw_json = cfg.model_dump_json(indent=2)
    console.print(
        Panel(
            Syntax(raw_json, "json", theme="monokai", line_numbers=True),
            title="⚙️  Configuración APA 7 Activa",
            border_style="blue",
        )
    )


@config_app.command("init")
def config_init(
    output: Annotated[
        str, typer.Option("--output", "-o", help="Nombre del archivo destino")
    ] = "apa7_config.json",
) -> None:
    """Copiar la configuración por defecto al directorio actual para personalización."""
    dest = Path(output)
    if dest.exists():
        console.print(f"[bold yellow]⚠️  El archivo ya existe:[/] {dest}")
        overwrite = typer.confirm("¿Desea sobrescribirlo?")
        if not overwrite:
            raise typer.Abort()

    shutil.copy2(_DEFAULT_CONFIG_PATH, dest)
    console.print(
        Panel(
            f"✅ Configuración copiada a: [bold green]{dest}[/]\n\n"
            "Edite este archivo y úselo con [bold]--config[/]:\n"
            f'  apa demo --config "{dest}"',
            title="⚙️  Config Init",
            border_style="green",
        )
    )


@config_app.command("validate")
def config_validate(
    config_file: Annotated[
        str, typer.Argument(help="Ruta al archivo JSON de configuración a validar")
    ],
) -> None:
    """Validar un archivo JSON de configuración APA 7."""
    path = Path(config_file)
    if not path.exists():
        console.print(f"[bold red]❌ Archivo no encontrado:[/] {path}")
        raise typer.Exit(code=1)

    try:
        cfg = load_config(path)
        console.print(
            Panel(
                f"✅ Configuración válida\n\n"
                f"  Norma: [cyan]{cfg.metadata.norma} {cfg.metadata.edicion} ed.[/]\n"
                f"  Idioma: [cyan]{cfg.metadata.idioma}[/]\n"
                f"  Fuentes: [cyan]{len(cfg.fuentes_aceptadas)}[/] definidas\n"
                f"  Niveles de título: [cyan]{len(cfg.jerarquia_titulos)}[/]",
                title="✅ Validation",
                border_style="green",
            )
        )
    except Exception as e:
        console.print(
            Panel(
                f"[bold red]❌ Error de validación:[/]\n\n{e}",
                title="❌ Validation Failed",
                border_style="red",
            )
        )
        raise typer.Exit(code=1)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _generate_document(
    doc: APADocument, output_path: Path, config: APAConfig | None = None
) -> Path:
    """Generate the document using the appropriate adapter."""
    if doc.output_format == OutputFormat.PDF:
        from apa_formatter.adapters.pdf_adapter import PdfAdapter

        adapter = PdfAdapter(doc, config=config)
    else:
        from apa_formatter.adapters.docx_adapter import DocxAdapter

        adapter = DocxAdapter(doc, config=config)

    return adapter.generate(output_path)


def _build_demo_document(font: FontChoice, output_format: OutputFormat) -> APADocument:
    """Build a comprehensive demo APA 7 document."""
    return APADocument(
        title_page=TitlePage(
            title="El Impacto de la Inteligencia Artificial en la Educación Superior: Una Revisión Sistemática",
            authors=["María García López", "Carlos Rodríguez Pérez"],
            affiliation="Universidad Nacional de Colombia",
            course="PSY 301: Métodos de Investigación",
            instructor="Dra. Ana Martínez",
            due_date=date.today(),
            variant=DocumentVariant.STUDENT,
        ),
        abstract=(
            "Este estudio examina el impacto de la inteligencia artificial (IA) en la educación "
            "superior a través de una revisión sistemática de la literatura publicada entre 2018 "
            "y 2024. Se analizaron 45 artículos de revistas indexadas utilizando un enfoque de "
            "síntesis temática. Los resultados indican que la IA tiene efectos significativos en "
            "tres áreas principales: personalización del aprendizaje, evaluación automatizada y "
            "accesibilidad educativa. Sin embargo, también se identificaron desafíos importantes "
            "relacionados con la equidad, la privacidad de datos y la formación docente. Las "
            "implicaciones para la práctica educativa y futuras líneas de investigación se discuten."
        ),
        keywords=[
            "inteligencia artificial",
            "educación superior",
            "aprendizaje personalizado",
            "revisión sistemática",
        ],
        font=font,
        output_format=output_format,
        sections=[
            Section(
                heading="Introduction",
                level=HeadingLevel.LEVEL_1,
                content=(
                    "La inteligencia artificial (IA) ha transformado diversos sectores de la sociedad "
                    "en las últimas décadas, y la educación superior no ha sido la excepción. Desde "
                    "los sistemas de tutoría inteligente hasta los chatbots educativos, las aplicaciones "
                    "de IA en el ámbito universitario continúan expandiéndose a un ritmo acelerado "
                    "(Smith & Jones, 2022).\n\n"
                    "La presente investigación tiene como objetivo principal analizar y sintetizar la "
                    "evidencia científica disponible sobre el impacto de la IA en la educación superior. "
                    "Específicamente, se busca identificar las principales áreas de aplicación, los "
                    "beneficios documentados, los desafíos encontrados y las recomendaciones para una "
                    "implementación efectiva (Brown et al., 2023)."
                ),
            ),
            Section(
                heading="Method",
                level=HeadingLevel.LEVEL_1,
                content=(
                    "Se utilizó un diseño de revisión sistemática siguiendo las directrices PRISMA "
                    "(Page et al., 2021). Este enfoque permitió una evaluación rigurosa y transparente "
                    "de la literatura existente."
                ),
                subsections=[
                    Section(
                        heading="Search Strategy",
                        level=HeadingLevel.LEVEL_2,
                        content=(
                            "La búsqueda se realizó en tres bases de datos: PsycINFO, ERIC y Scopus. "
                            "Se utilizaron los términos de búsqueda 'artificial intelligence' AND "
                            "'higher education' OR 'university education', limitando los resultados a "
                            "artículos publicados entre 2018 y 2024 en inglés o español."
                        ),
                        subsections=[
                            Section(
                                heading="Inclusion Criteria",
                                level=HeadingLevel.LEVEL_3,
                                content=(
                                    "Se incluyeron artículos que: (a) fueron publicados en revistas "
                                    "revisadas por pares, (b) abordaron directamente el uso de IA en "
                                    "contextos de educación superior, y (c) presentaron evidencia "
                                    "empírica o análisis sistemáticos."
                                ),
                                subsections=[
                                    Section(
                                        heading="Quality Assessment",
                                        level=HeadingLevel.LEVEL_4,
                                        content=(
                                            "Cada artículo fue evaluado utilizando la escala de "
                                            "calidad de estudios mixtos (MMAT) por dos revisores "
                                            "independientes."
                                        ),
                                    ),
                                    Section(
                                        heading="Inter-rater reliability",
                                        level=HeadingLevel.LEVEL_5,
                                        content=(
                                            "El acuerdo entre evaluadores se calculó utilizando "
                                            "el coeficiente kappa de Cohen, obteniendo un valor "
                                            "de κ = 0.87, indicando un alto nivel de concordancia."
                                        ),
                                    ),
                                ],
                            ),
                        ],
                    ),
                    Section(
                        heading="Data Analysis",
                        level=HeadingLevel.LEVEL_2,
                        content=(
                            "Se empleó un análisis temático inductivo para identificar patrones y "
                            "temas recurrentes en los artículos seleccionados. Los datos fueron "
                            "codificados utilizando el software NVivo 14."
                        ),
                    ),
                ],
            ),
            Section(
                heading="Results",
                level=HeadingLevel.LEVEL_1,
                content=(
                    "El análisis de los 45 artículos incluidos reveló tres temas principales: "
                    "(a) personalización del aprendizaje, (b) evaluación automatizada, y "
                    "(c) accesibilidad educativa. Cada tema se describe en detalle a continuación."
                ),
                subsections=[
                    Section(
                        heading="Personalized Learning",
                        level=HeadingLevel.LEVEL_2,
                        content=(
                            "El 78% de los estudios revisados identificaron la personalización del "
                            "aprendizaje como el beneficio más significativo de la IA en educación "
                            "superior. Los sistemas adaptativos de aprendizaje mostraron mejoras "
                            "estadísticamente significativas en el rendimiento académico de los "
                            "estudiantes (d = 0.45, IC 95% [0.32, 0.58])."
                        ),
                    ),
                    Section(
                        heading="Automated Assessment",
                        level=HeadingLevel.LEVEL_2,
                        content=(
                            "Los sistemas de evaluación automatizada basados en IA demostraron una "
                            "correlación positiva con las evaluaciones humanas (r = 0.89, p < .001), "
                            "sugiriendo que estos sistemas pueden ser herramientas complementarias "
                            "confiables para los docentes."
                        ),
                    ),
                ],
            ),
            Section(
                heading="Discussion",
                level=HeadingLevel.LEVEL_1,
                content=(
                    "Los hallazgos de esta revisión son consistentes con investigaciones previas que "
                    "señalan el potencial transformador de la IA en la educación (García & López, 2021). "
                    "Sin embargo, es crucial abordar los desafíos éticos y de equidad que acompañan "
                    "la implementación de estas tecnologías.\n\n"
                    "Las limitaciones de este estudio incluyen el enfoque exclusivo en artículos en "
                    "inglés y español, lo que puede haber excluido investigaciones relevantes en otros "
                    "idiomas. Futuras investigaciones deberían explorar el impacto a largo plazo de la "
                    "IA en los resultados de aprendizaje y considerar contextos culturales diversos."
                ),
            ),
        ],
        references=[
            Reference(
                ref_type=ReferenceType.JOURNAL_ARTICLE,
                authors=[
                    Author(last_name="Smith", first_name="John", middle_initial="A"),
                    Author(last_name="Jones", first_name="Maria"),
                ],
                year=2022,
                title="Artificial intelligence in higher education: A systematic review",
                source="Journal of Educational Technology",
                volume="15",
                issue="3",
                pages="234-256",
                doi="10.1234/jet.2022.15.3.234",
            ),
            Reference(
                ref_type=ReferenceType.JOURNAL_ARTICLE,
                authors=[
                    Author(last_name="Brown", first_name="Emily"),
                    Author(last_name="Davis", first_name="Robert", middle_initial="K"),
                    Author(last_name="Wilson", first_name="Sarah"),
                ],
                year=2023,
                title="Machine learning applications in university settings: Benefits and challenges",
                source="Computers & Education",
                volume="198",
                pages="104-121",
                doi="10.1016/j.compedu.2023.104",
            ),
            Reference(
                ref_type=ReferenceType.JOURNAL_ARTICLE,
                authors=[
                    Author(last_name="García", first_name="Pedro"),
                    Author(last_name="López", first_name="Carmen", middle_initial="R"),
                ],
                year=2021,
                title="Transformación digital en universidades latinoamericanas",
                source="Revista de Educación Superior",
                volume="50",
                issue="2",
                pages="45-67",
                doi="10.36857/resu.2021.50.2.45",
            ),
            Reference(
                ref_type=ReferenceType.JOURNAL_ARTICLE,
                authors=[
                    Author(last_name="Page", first_name="Matthew", middle_initial="J"),
                    Author(last_name="McKenzie", first_name="Joanne", middle_initial="E"),
                    Author(last_name="Bossuyt", first_name="Patrick", middle_initial="M"),
                ],
                year=2021,
                title="The PRISMA 2020 statement: An updated guideline for reporting systematic reviews",
                source="BMJ",
                volume="372",
                pages="n71",
                doi="10.1136/bmj.n71",
            ),
            Reference(
                ref_type=ReferenceType.BOOK,
                authors=[
                    Author(last_name="American Psychological Association", first_name="American")
                ],
                year=2020,
                title="Publication manual of the American Psychological Association",
                source="American Psychological Association",
                edition="7",
                doi="10.1037/0000165-000",
            ),
        ],
        appendices=[
            Section(
                heading="Search Terms Used in Database Queries",
                level=HeadingLevel.LEVEL_1,
                content=(
                    "The following search strings were used across all three databases:\n\n"
                    '1. ("artificial intelligence" OR "machine learning" OR "deep learning") AND '
                    '("higher education" OR "university" OR "college")\n\n'
                    '2. ("AI-powered" OR "intelligent tutoring") AND ("student outcomes" OR '
                    '"academic performance")\n\n'
                    '3. ("educational technology" OR "EdTech") AND ("artificial intelligence") AND '
                    '("assessment" OR "evaluation")'
                ),
            ),
        ],
    )


if __name__ == "__main__":
    app()
