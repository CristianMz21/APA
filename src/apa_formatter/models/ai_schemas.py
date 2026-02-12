"""Pydantic schemas for AI-structured document analysis output.

These models define the JSON schema that Gemini must follow when returning
structured data.  They map closely to the existing ``SemanticDocument``
hierarchy but are intentionally decoupled — AI output is *merged* into the
mechanical extraction, not used directly as the final result.

Usage::

    from apa_formatter.models.ai_schemas import AiSemanticResult

    # Generate JSON schema for Gemini
    schema = AiSemanticResult.model_json_schema()

    # Parse Gemini JSON response
    result = AiSemanticResult.model_validate(gemini_json)
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class AiTitlePage(BaseModel):
    """Title page metadata extracted by AI."""

    title: str = Field(description="Título principal del documento")
    authors: list[str] = Field(
        default_factory=list,
        description="Lista de autores del documento",
    )
    university: str | None = Field(
        default=None,
        description="Universidad o institución afiliada",
    )
    course: str | None = Field(
        default=None,
        description="Nombre del curso o asignatura",
    )
    instructor: str | None = Field(
        default=None,
        description="Nombre del profesor o instructor",
    )
    due_date: str | None = Field(
        default=None,
        description="Fecha de entrega o presentación",
    )


class AiSection(BaseModel):
    """A document section identified by AI."""

    heading_level: int = Field(
        ge=1,
        le=5,
        description="Nivel de encabezado APA (1-5)",
    )
    title: str = Field(description="Título de la sección")
    content_summary: str = Field(
        default="",
        description="Resumen breve del contenido de la sección",
    )


class AiReference(BaseModel):
    """A bibliographic reference parsed by AI."""

    raw_text: str = Field(description="Texto completo de la referencia tal como aparece")
    authors: list[str] | None = Field(
        default=None,
        description="Autores extraídos de la referencia",
    )
    year: str | None = Field(
        default=None,
        description="Año de publicación",
    )
    title: str | None = Field(
        default=None,
        description="Título de la obra",
    )
    source: str | None = Field(
        default=None,
        description="Revista, editorial u origen de la publicación",
    )


class AiSemanticResult(BaseModel):
    """Full structured result returned by Gemini for a document chunk.

    This schema is sent to Gemini via ``response_json_schema`` to enforce
    strict JSON output.
    """

    title_page: AiTitlePage | None = Field(
        default=None,
        description="Datos de la portada (si se detecta)",
    )
    abstract: str | None = Field(
        default=None,
        description="Texto del resumen/abstract",
    )
    keywords: list[str] = Field(
        default_factory=list,
        description="Palabras clave del documento",
    )
    sections: list[AiSection] = Field(
        default_factory=list,
        description="Secciones del documento con sus niveles de encabezado",
    )
    references: list[AiReference] = Field(
        default_factory=list,
        description="Referencias bibliográficas al final del documento",
    )
