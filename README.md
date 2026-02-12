# APA Formatter

Formateador de documentos Word (.docx) y PDF conforme a las **normas APA 7ª edición**.

## Instalación

```bash
pip install -e .
```

## Uso

```bash
# Crear documento de ejemplo
apa demo --output ejemplo.docx

# Crear documento con parámetros
apa create --title "Mi Investigación" --author "Juan Pérez" --output paper.docx

# Convertir a PDF
apa convert paper.docx --to pdf
```

## Características

- ✅ Márgenes de 1 pulgada
- ✅ Times New Roman 12pt / Calibri 11pt / Arial 11pt
- ✅ Doble espacio
- ✅ Página de título (estudiante y profesional)
- ✅ 5 niveles de encabezados APA
- ✅ Running head y numeración de páginas
- ✅ Lista de referencias con sangría francesa
- ✅ Generación Word (.docx) y PDF


## Licencia

Este proyecto está licenciado bajo la Licencia Pública General de GNU v3.0 (GPLv3). Consulte el archivo [LICENSE](LICENSE) para más detalles.

