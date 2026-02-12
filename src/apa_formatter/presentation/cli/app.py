"""Thin CLI wrapper — Typer commands that delegate to Use Cases.

All domain logic is accessed through the Container (bootstrap.py).
No direct imports from adapters/ or config/loader here.
"""

from __future__ import annotations

import shutil
from datetime import date
from pathlib import Path
from typing import Annotated, Optional

import typer

from apa_formatter.presentation.cli.formatters import (
    compliance_table,
    console,
    error_message,
    json_panel,
    rules_table,
    success_panel,
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


# ---------------------------------------------------------------------------
# apa create
# ---------------------------------------------------------------------------


@app.command()
def create(
    title: Annotated[str, typer.Option("--title", "-t", help="Título del trabajo")],
    author: Annotated[
        Optional[list[str]], typer.Option("--author", "-a", help="Nombre(s) del autor")
    ] = None,
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
    font: Annotated[str, typer.Option("--font", "-f", help="Fuente a usar")] = "Times New Roman",
    variant: Annotated[
        str,
        typer.Option("--variant", "-v", help="Tipo de paper (student/professional)"),
    ] = "student",
    output: Annotated[
        str, typer.Option("--output", "-o", help="Archivo de salida (.docx o .pdf)")
    ] = "document.docx",
    config: Annotated[
        Optional[str],
        typer.Option("--config", "-c", help="Ruta a archivo JSON de configuración"),
    ] = None,
) -> None:
    """Crear un documento APA 7 con los parámetros especificados."""
    from apa_formatter.bootstrap import Container
    from apa_formatter.domain.models.document import APADocument, Section, TitlePage
    from apa_formatter.domain.models.enums import (
        DocumentVariant,
        FontChoice,
        HeadingLevel,
        OutputFormat,
    )

    authors = author or ["Autor Desconocido"]
    out_format = OutputFormat.PDF if output.endswith(".pdf") else OutputFormat.DOCX
    font_choice = FontChoice(font)
    doc_variant = DocumentVariant(variant)

    title_page = TitlePage(
        title=title,
        authors=authors,
        affiliation=affiliation,
        course=course,
        instructor=instructor,
        due_date=date.today(),
        variant=doc_variant,
    )

    doc = APADocument(
        title_page=title_page,
        abstract=abstract,
        font=font_choice,
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

    container = Container(config_path=config)
    uc = container.create_document(out_format)
    output_path = uc.execute(doc, Path(output))

    success_panel(f"✅ Documento creado: [bold green]{output_path}[/]")


# ---------------------------------------------------------------------------
# apa demo
# ---------------------------------------------------------------------------


@app.command()
def demo(
    output: Annotated[
        str, typer.Option("--output", "-o", help="Archivo de salida")
    ] = "demo_apa7.docx",
    font: Annotated[str, typer.Option("--font", "-f", help="Fuente")] = "Times New Roman",
    config: Annotated[
        Optional[str],
        typer.Option("--config", "-c", help="Ruta a archivo JSON de configuración"),
    ] = None,
) -> None:
    """Generar un documento de ejemplo completo con todas las características APA 7."""
    from apa_formatter.bootstrap import Container
    from apa_formatter.domain.models.enums import FontChoice, OutputFormat

    out_format = OutputFormat.PDF if output.endswith(".pdf") else OutputFormat.DOCX
    font_choice = FontChoice(font)

    container = Container(config_path=config)
    uc = container.generate_demo()
    doc = uc.execute(font=font_choice, output_format=out_format)

    render_uc = container.create_document(out_format)
    output_path = render_uc.execute(doc, Path(output))

    success_panel(
        f"✅ Documento de ejemplo generado: [bold green]{output_path}[/]\n\n"
        "📋 Incluye:\n"
        "  • Página de título APA 7 (estudiante)\n"
        "  • Abstract con palabras clave\n"
        "  • Secciones con 5 niveles de encabezados\n"
        "  • Lista de referencias con sangría francesa\n"
        "  • Apéndice de ejemplo",
        title="🎓 APA 7 Demo",
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
        error_message(f"Archivo no encontrado: {source}")
        raise typer.Exit(code=1)

    if source_path.suffix.lower() != ".docx":
        error_message("Solo se soporta conversión de .docx a .pdf")
        raise typer.Exit(code=1)

    out_path = Path(output) if output else source_path.with_suffix(".pdf")

    try:
        result = docx_to_pdf(source_path, out_path)
        success_panel(
            f"✅ Convertido exitosamente:\n"
            f"  📥 Fuente: [cyan]{source_path}[/]\n"
            f"  📤 Salida: [bold green]{result}[/]\n\n"
            f"[dim]Nota: El contenido se re-formatea según APA 7 durante la conversión.[/]",
            title="🔄 APA Convert",
        )
    except Exception as e:
        error_message(f"Error durante la conversión: {e}")
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
        error_message(f"Archivo no encontrado: {source}")
        raise typer.Exit(code=1)

    try:
        checker = APAChecker(source_path)
        report = checker.check()
    except (FileNotFoundError, ValueError) as e:
        error_message(str(e))
        raise typer.Exit(code=1)

    compliance_table(report)


# ---------------------------------------------------------------------------
# apa info
# ---------------------------------------------------------------------------


@app.command()
def info() -> None:
    """Mostrar las reglas APA 7 implementadas."""
    from apa_formatter.rules.constants import FONT_SPECS, HEADING_STYLES

    rules_table(FONT_SPECS, HEADING_STYLES)


# ---------------------------------------------------------------------------
# apa config show / init / validate
# ---------------------------------------------------------------------------


@config_app.command("show")
def config_show(
    config: Annotated[
        Optional[str],
        typer.Option("--config", "-c", help="Ruta a archivo JSON de configuración"),
    ] = None,
) -> None:
    """Mostrar la configuración APA 7 activa (formateada)."""
    from apa_formatter.config import get_config, load_config

    cfg = load_config(Path(config)) if config else get_config()
    raw_json = cfg.model_dump_json(indent=2)
    json_panel(raw_json)


@config_app.command("init")
def config_init(
    output: Annotated[
        str, typer.Option("--output", "-o", help="Nombre del archivo destino")
    ] = "apa7_config.json",
) -> None:
    """Copiar la configuración por defecto al directorio actual para personalización."""
    from apa_formatter.config.loader import _DEFAULT_CONFIG_PATH

    dest = Path(output)
    if dest.exists():
        console.print(f"[bold yellow]⚠️  El archivo ya existe:[/] {dest}")
        overwrite = typer.confirm("¿Desea sobrescribirlo?")
        if not overwrite:
            raise typer.Abort()

    shutil.copy2(_DEFAULT_CONFIG_PATH, dest)
    success_panel(
        f"✅ Configuración copiada a: [bold green]{dest}[/]\n\n"
        "Edite este archivo y úselo con [bold]--config[/]:\n"
        f'  apa demo --config "{dest}"',
        title="⚙️  Config Init",
    )


@config_app.command("validate")
def config_validate(
    config_file: Annotated[
        str, typer.Argument(help="Ruta al archivo JSON de configuración a validar")
    ],
) -> None:
    """Validar un archivo JSON de configuración APA 7."""
    from apa_formatter.config import load_config

    path = Path(config_file)
    if not path.exists():
        error_message(f"Archivo no encontrado: {path}")
        raise typer.Exit(code=1)

    try:
        cfg = load_config(path)
        success_panel(
            f"✅ Configuración válida\n\n"
            f"  Norma: [cyan]{cfg.metadata.norma} {cfg.metadata.edicion} ed.[/]\n"
            f"  Idioma: [cyan]{cfg.metadata.idioma}[/]\n"
            f"  Fuentes: [cyan]{len(cfg.fuentes_aceptadas)}[/] definidas\n"
            f"  Niveles de título: [cyan]{len(cfg.jerarquia_titulos)}[/]",
            title="✅ Validation",
        )
    except Exception as e:
        console.print(
            f"[bold red]❌ Error de validación:[/]\n\n{e}",
        )
        raise typer.Exit(code=1)


if __name__ == "__main__":
    app()
