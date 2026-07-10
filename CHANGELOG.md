# Changelog

Todas las modificaciones relevantes de este proyecto se documentan acá.
Formato basado en [Keep a Changelog](https://keepachangelog.com/es-AR/1.1.0/);
versionado [semántico](https://semver.org/lang/es/).

## [0.3.0] — 2026-07-10

### Añadido
- **Flujo de inicio guiado**: al abrir una sesión nueva, el sistema pregunta
  qué juego se jugará, pide el manual básico (PDF) y luego la planilla del
  jugador (PDF), sin intervención del LLM durante el setup.
- **Parser de planillas** (`narrator/core/sheet_parser.py`): la planilla
  adjunta se extrae con PyMuPDF y se estructura vía LLM a JSON para poblar
  la hoja de personaje. Reusable por el futuro Rule Arbiter.
- Botón "Planilla" en el header para (re)abrir el diálogo de carga.
- Tests del parser de planillas (8 casos).

### Cambiado
- **Creación de personaje in-app pospuesta**: se elimina el prompt de
  creación tras cargar el manual; el narrador usa la planilla provista y no
  inventa datos del personaje.
- **Layout responsive**: la GUI se reajusta al tamaño real del viewport
  (resize y barra de progreso incluidos); el input del chat y todos los
  botones quedan siempre visibles.
- "Nueva sesión" conserva el manual cargado y re-pide solo la planilla.

### Arreglado
- `pip install -e .` fallaba por descubrimiento de múltiples paquetes
  top-level en flat-layout (`data`, `config`, `narrator`); se limita el
  discovery a `narrator*` y se incluyen los YAML como package-data.

## [0.2.0] — anterior

- Motor de rol con agentes especializados y LLMs locales vía Ollama
  (base heredada; ver README).
