"""Use Case: Generate Demo Document.

Builds a comprehensive demo APA 7 document for testing/showcase.
"""

from datetime import date

from apa_formatter.domain.models.document import APADocument, Section, TitlePage
from apa_formatter.domain.models.enums import (
    DocumentVariant,
    FontChoice,
    HeadingLevel,
    OutputFormat,
    ReferenceType,
)
from apa_formatter.domain.models.reference import Author, Reference


class GenerateDemoUseCase:
    """Build a sample APA 7 document with realistic content."""

    def execute(
        self,
        font: FontChoice = FontChoice.TIMES_NEW_ROMAN,
        output_format: OutputFormat = OutputFormat.DOCX,
    ) -> APADocument:
        """Return a fully populated demo document.

        Args:
            font: Which APA-approved font to use.
            output_format: DOCX or PDF.

        Returns:
            A complete APADocument ready for rendering.
        """
        return APADocument(
            title_page=TitlePage(
                title=(
                    "El Impacto de la Inteligencia Artificial en la Educación Superior: "
                    "Una Revisión Sistemática"
                ),
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
            sections=self._build_sections(),
            references=self._build_references(),
            appendices=self._build_appendices(),
        )

    @staticmethod
    def _build_sections() -> list[Section]:
        """Build the demo document body sections."""
        return [
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
        ]

    @staticmethod
    def _build_references() -> list[Reference]:
        """Build the demo reference list."""
        return [
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
        ]

    @staticmethod
    def _build_appendices() -> list[Section]:
        """Build appendix sections."""
        return [
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
        ]
