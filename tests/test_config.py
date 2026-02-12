"""Tests for the APA 7 configuration system."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from apa_formatter.config.loader import clear_cache, load_config
from apa_formatter.config.models import APAConfig


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _fresh_cache():
    """Ensure a clean config cache for every test."""
    clear_cache()
    yield
    clear_cache()


# ---------------------------------------------------------------------------
# Default config loading
# ---------------------------------------------------------------------------


class TestDefaultConfig:
    """Tests for loading the built-in apa7_default.json."""

    def test_loads_without_error(self):
        cfg = load_config()
        assert isinstance(cfg, APAConfig)

    def test_metadata(self):
        cfg = load_config()
        assert cfg.metadata.norma == "APA"
        assert cfg.metadata.edicion == "7ma"
        assert cfg.metadata.idioma == "Español"
        assert cfg.metadata.fuente_origen == "Guia-Normas-APA-7ma-edicion.pdf"

    def test_page_config_margins(self):
        cfg = load_config()
        m = cfg.configuracion_pagina.margenes
        assert m.superior_cm == 2.54
        assert m.inferior_cm == 2.54
        assert m.izquierda_cm == 2.54
        assert m.derecha_cm == 2.54
        # Inch conversion
        assert abs(m.superior_inches - 1.0) < 1e-9

    def test_page_config_paper(self):
        cfg = load_config()
        p = cfg.configuracion_pagina.tamaño_papel
        assert p.nombre == "Carta"
        assert p.ancho_cm == 21.59
        assert abs(p.ancho_inches - 8.5) < 0.01

    def test_pagination(self):
        cfg = load_config()
        pag = cfg.configuracion_pagina.paginacion
        assert pag.ubicacion == "esquina_superior_derecha"
        assert pag.inicio == "portada_numero_1"
        assert pag.formato == "numeros_arabigos"

    def test_fonts_count(self):
        cfg = load_config()
        assert len(cfg.fuentes_aceptadas) == 6

    def test_times_new_roman_present(self):
        cfg = load_config()
        tnr = cfg.get_font("Times New Roman")
        assert tnr is not None
        assert tnr.tamaño_pt == 12

    def test_font_exceptions(self):
        cfg = load_config()
        exc = cfg.fuentes_y_tipografia.excepciones
        assert exc.figuras.tamaño_min_pt == 8
        assert exc.figuras.tamaño_max_pt == 14
        assert "Lucida Console" in exc.codigo_fuente.fuentes
        assert exc.notas_al_pie.interlineado == "sencillo"

    def test_text_format(self):
        cfg = load_config()
        fmt = cfg.formato_texto
        assert fmt.alineacion == "izquierda"
        assert fmt.justificado is False
        assert fmt.interlineado_general == 2.0
        assert fmt.sangria_parrafo.medida_cm == 1.27
        assert abs(fmt.sangria_parrafo.medida_inches - 0.5) < 0.01
        assert fmt.espaciado_parrafos.anterior_pt == 0
        assert fmt.espaciado_parrafos.posterior_pt == 0

    def test_headings_count(self):
        cfg = load_config()
        assert len(cfg.jerarquia_titulos) == 5

    def test_heading_level_1(self):
        cfg = load_config()
        h1 = cfg.get_heading(1)
        assert h1 is not None
        assert h1.is_centered is True
        assert h1.is_bold is True
        assert h1.is_italic is False
        assert h1.is_inline is False

    def test_heading_level_5(self):
        cfg = load_config()
        h5 = cfg.get_heading(5)
        assert h5 is not None
        assert h5.is_centered is False
        assert h5.is_bold is True
        assert h5.is_italic is True
        assert h5.is_inline is True
        assert h5.is_indented is True

    def test_document_elements(self):
        cfg = load_config()
        el = cfg.elementos_documento
        assert "portada" in el.orden_secciones
        assert "resumen" in el.orden_secciones
        assert "numero_pagina" in el.portada.estudiante
        assert "titulo_corto_header" in el.portada.profesional
        assert el.resumen.titulo == "Resumen"
        assert el.resumen.limite_palabras_max == 250
        assert el.resumen.palabras_clave.etiqueta == "Palabras clave:"

    def test_citation_rules(self):
        cfg = load_config()
        citas = cfg.citas
        assert citas.reglas_generales.sistema == "autor-fecha"
        assert citas.cita_textual_corta.max_palabras == 39
        assert citas.cita_textual_bloque.min_palabras == 40
        assert citas.cita_textual_bloque.comillas is False
        assert abs(citas.cita_textual_bloque.sangria_bloque_inches - 0.5) < 0.01
        assert citas.parafraseo.requiere == ["apellido", "año"]
        assert citas.autores.tres_o_mas_autores == "Apellido1 et al. (Año)"

    def test_reference_config(self):
        cfg = load_config()
        refs = cfg.referencias
        assert refs.formato_lista.titulo == "Referencias"
        assert abs(refs.formato_lista.sangria_francesa_inches - 0.5) < 0.01
        assert refs.limite_autores_mostrar.hasta == 20
        assert "autor" in refs.elementos_basicos
        assert refs.casos_especiales.sin_fecha == "s.f."

    def test_tables_and_figures(self):
        cfg = load_config()
        tf = cfg.tablas_y_figuras
        assert tf.numeracion.estilo == "negrita"
        assert tf.titulo.estilo == "cursiva"
        assert tf.tablas.bordes_verticales is False
        assert tf.notas.prefijo == "Nota."


# ---------------------------------------------------------------------------
# Custom config / overrides
# ---------------------------------------------------------------------------


class TestCustomConfig:
    """Tests for loading custom JSON config files."""

    def test_custom_margins(self, tmp_path):
        custom = {
            "configuracion_pagina": {
                "margenes": {
                    "superior_cm": 3.0,
                    "inferior_cm": 3.0,
                    "izquierda_cm": 3.0,
                    "derecha_cm": 3.0,
                }
            }
        }
        path = tmp_path / "custom.json"
        path.write_text(json.dumps(custom))

        cfg = load_config(path)
        assert cfg.configuracion_pagina.margenes.superior_cm == 3.0
        # Defaults still applied
        assert cfg.metadata.norma == "APA"

    def test_file_not_found(self):
        with pytest.raises(FileNotFoundError):
            load_config(Path("/nonexistent/config.json"))

    def test_invalid_json_raises_error(self, tmp_path):
        bad = tmp_path / "bad.json"
        bad.write_text("not json {{{")
        with pytest.raises(Exception):
            load_config(bad)

    def test_invalid_heading_level(self, tmp_path):
        custom = {
            "jerarquia_titulos": [
                {
                    "nivel": 99,
                    "formato": {"negrita": True},
                }
            ]
        }
        path = tmp_path / "bad_heading.json"
        path.write_text(json.dumps(custom))
        with pytest.raises(ValidationError):
            load_config(path)


# ---------------------------------------------------------------------------
# Caching
# ---------------------------------------------------------------------------


class TestCaching:
    """Tests for the config caching mechanism."""

    def test_returns_same_instance(self):
        a = load_config()
        b = load_config()
        assert a is b

    def test_cache_cleared(self):
        a = load_config()
        clear_cache()
        b = load_config()
        # New object after clear
        assert a is not b
        # But content identical
        assert a.metadata == b.metadata


# ---------------------------------------------------------------------------
# Constants bridge
# ---------------------------------------------------------------------------


class TestConstantsBridge:
    """Test that rules/constants.py correctly reads from config."""

    def test_font_specs_from_config(self):
        from apa_formatter.models.enums import FontChoice
        from apa_formatter.rules.constants import FONT_SPECS

        assert FontChoice.TIMES_NEW_ROMAN in FONT_SPECS
        assert FONT_SPECS[FontChoice.TIMES_NEW_ROMAN].size_pt == 12

    def test_heading_styles_from_config(self):
        from apa_formatter.rules.constants import HEADING_STYLES

        assert 1 in HEADING_STYLES
        assert HEADING_STYLES[1].centered is True
        assert HEADING_STYLES[5].inline is True

    def test_margin_inches(self):
        from apa_formatter.rules.constants import MARGIN_INCHES

        assert abs(MARGIN_INCHES - 1.0) < 0.01

    def test_line_spacing(self):
        from apa_formatter.rules.constants import LINE_SPACING

        assert LINE_SPACING == 2.0


# ---------------------------------------------------------------------------
# SENA config
# ---------------------------------------------------------------------------

SENA_CONFIG_PATH = (
    Path(__file__).resolve().parent.parent
    / "src"
    / "apa_formatter"
    / "config"
    / "sena_default.json"
)


class TestSENAConfig:
    """Tests for loading the SENA institutional config profile."""

    def test_loads_without_error(self):
        cfg = load_config(SENA_CONFIG_PATH)
        assert isinstance(cfg, APAConfig)

    def test_is_institutional(self):
        cfg = load_config(SENA_CONFIG_PATH)
        assert cfg.is_institutional is True

    def test_institutional_metadata(self):
        cfg = load_config(SENA_CONFIG_PATH)
        meta = cfg.metadatos_norma
        assert meta is not None
        assert meta.institucion == "Servicio Nacional de Aprendizaje (SENA)"
        assert meta.base == "APA 7ma Edición"
        assert meta.año_documento == 2020

    def test_binding_margins(self):
        cfg = load_config(SENA_CONFIG_PATH)
        emp = cfg.configuracion_pagina.margenes.condicion_empaste
        assert emp is not None
        assert emp.izquierda_cm == 4.0
        assert abs(emp.izquierda_inches - (4.0 / 2.54)) < 1e-9

    def test_fonts_count_5(self):
        cfg = load_config(SENA_CONFIG_PATH)
        assert len(cfg.fuentes_aceptadas) == 5
        names = {f.nombre for f in cfg.fuentes_aceptadas}
        assert "Computer Modern" not in names
        assert "Times New Roman" in names

    def test_table_content_font(self):
        cfg = load_config(SENA_CONFIG_PATH)
        fc = cfg.tablas_y_figuras.fuente_contenido
        assert fc is not None
        assert fc.tamaño_pt == 10

    def test_table_visual_format(self):
        cfg = load_config(SENA_CONFIG_PATH)
        vf = cfg.tablas_y_figuras.formato_visual
        assert vf is not None
        assert vf.lineas_horizontales == 3
        assert vf.lineas_verticales is False

    def test_legal_references(self):
        cfg = load_config(SENA_CONFIG_PATH)
        leg = cfg.referencias_legales_colombia
        assert leg is not None
        assert "constitucion" in leg.formatos_plantilla
        assert "leyes" in leg.formatos_plantilla
        assert "codigos" in leg.formatos_plantilla
        assert "sentencias" in leg.formatos_plantilla
        assert "actos_administrativos" in leg.formatos_plantilla
        # Check a template
        const = leg.formatos_plantilla["constitucion"]
        assert "Constitución" in const.ejemplo

    def test_default_config_not_institutional(self):
        """The base APA config should NOT be institutional."""
        clear_cache()
        cfg = load_config()
        assert cfg.is_institutional is False
        assert cfg.referencias_legales_colombia is None
