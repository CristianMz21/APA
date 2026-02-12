---
description: Verificar que el código respeta las reglas de Clean Architecture (regla de dependencia, estructura de capas, convenciones de puertos y use cases)
---

# /check-architecture — Verificación de Clean Architecture

## Paso 1: Leer las reglas de arquitectura

Lee el archivo `@ARCHITECTURE.md` en la raíz del proyecto para entender las reglas vigentes.

## Paso 2: Verificar la Regla de Dependencia

// turbo
Ejecutar los siguientes comandos grep para detectar violaciones de la regla de dependencia. **El resultado debe estar vacío** para cada comando:

```bash
echo "=== 1. Domain → Infrastructure/Presentation (PROHIBIDO) ===" && \
grep -rn "from apa_formatter\.\(infrastructure\|presentation\|adapters\|config\.loader\)" src/apa_formatter/domain/ 2>/dev/null || echo "✅ Sin violaciones" && \
echo "" && \
echo "=== 2. Application → Infrastructure/Presentation (PROHIBIDO) ===" && \
grep -rn "from apa_formatter\.\(infrastructure\|presentation\)" src/apa_formatter/application/ 2>/dev/null || echo "✅ Sin violaciones" && \
echo "" && \
echo "=== 3. Presentation → Infrastructure directa (PROHIBIDO, debe usar Container) ===" && \
grep -rn "from apa_formatter\.infrastructure\." src/apa_formatter/presentation/ 2>/dev/null || echo "✅ Sin violaciones"
```

Si hay violaciones, reportarlas con el archivo exacto, la línea, y la corrección sugerida.

## Paso 3: Verificar que los Ports son ABCs puras

// turbo
Verificar que todos los archivos en `domain/ports/` solo contienen ABCs sin imports de infrastructure:

```bash
echo "=== Ports con imports sospechosos ===" && \
grep -rn "from apa_formatter\.\(infrastructure\|adapters\|config\.loader\|presentation\)" src/apa_formatter/domain/ports/ 2>/dev/null || echo "✅ Todos los ports son puros"
```

## Paso 4: Verificar que los Use Cases no importan clases concretas

// turbo
Verificar que `application/use_cases/` solo importa de `domain/`:

```bash
echo "=== Use Cases con imports de clases concretas ===" && \
grep -rn "from apa_formatter\.\(infrastructure\|adapters\|config\.loader\|presentation\|fetchers\|validators\|converters\)" src/apa_formatter/application/use_cases/ 2>/dev/null || echo "✅ Todos los use cases respetan la regla"
```

## Paso 5: Verificar que bootstrap.py es el único Composition Root

// turbo
Solo `bootstrap.py` debe importar de `infrastructure/`. Verificar que ningún otro archivo en `presentation/` importa directamente de `infrastructure/`:

```bash
echo "=== Archivos fuera de bootstrap.py que importan infrastructure ===" && \
grep -rln "from apa_formatter\.infrastructure\." src/apa_formatter/ --include="*.py" | grep -v "bootstrap.py" | grep -v "infrastructure/" | grep -v "__pycache__" || echo "✅ Solo bootstrap.py importa de infrastructure"
```

## Paso 6: Ejecutar tests

// turbo
Ejecutar el test suite completo para verificar que no hay regresiones:

```bash
python -m pytest tests/ -x -q --tb=short 2>&1 | tail -10
```

Verificar que **todos los tests pasan** (286+).

## Paso 7: Generar reporte

Presentar un resumen con formato tabla:

| Verificación | Estado |
|---|---|
| Domain → Infra/Presentation | ✅ o ❌ |
| Application → Infra/Presentation | ✅ o ❌ |
| Presentation → Infrastructure directa | ✅ o ❌ |
| Ports son ABCs puras | ✅ o ❌ |
| Use Cases sin clases concretas | ✅ o ❌ |
| bootstrap.py es único Composition Root | ✅ o ❌ |
| Tests pasan | ✅ o ❌ (N tests) |

Si hay ❌, listar cada violación con archivo, línea y corrección sugerida.
