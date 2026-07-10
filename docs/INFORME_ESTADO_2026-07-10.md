# Informe de Estado — AI NARRATOR

**Fecha:** 2026-07-10 · **Versión:** 0.6.0 · **Tests:** 69/69 ✅

> **Premisa rectora del proyecto:** *"Un usuario carga un manual de reglas y un
> personaje, y puede jugar una aventura guiada por un Narrador IA."*
> Toda mejora se filtró contra esta premisa: lo que no la sirve directamente
> se difirió o descartó.

---

## 1. Qué se hizo (v0.2.0 → v0.6.0)

### Infraestructura

| Ítem | Detalle |
|---|---|
| Packaging | `pip install -e .` reparado (discovery de setuptools limitado a `narrator*`, YAMLs como package-data) |
| Changelog | `CHANGELOG.md` creado, mantenido por release, versionado semántico |
| Higiene | `.gitignore` cubre `*.egg-info/`, `build/`, `dist/` |
| Tests | Suite de 4 → **69 tests** (sheet parser, rule arbiter, memoria, psique, escenas, fronts) |

### Fase A — Flujo de inicio y UI (v0.3.0)

- **Layout responsive**: la GUI se recalcula en cada resize del viewport y al
  mostrar/ocultar la barra de progreso — el input del chat y todos los botones
  quedan siempre visibles (antes se calculaba una sola vez al maximizar).
- **Flujo de inicio guiado** (sin LLM): al abrir, el sistema pregunta qué juego
  se jugará → pide el manual básico (PDF) → pide la **planilla del jugador**
  (PDF). Fases: `setup_game → setup_manual → setup_sheet → play`.
- **Parser de planillas** (`narrator/core/sheet_parser.py`): PyMuPDF extrae el
  texto, el LLM lo estructura a JSON y puebla la hoja de personaje.
- **Creación de personaje in-app pospuesta** (decisión de alcance): el narrador
  usa la planilla provista y no inventa datos del personaje.

### Fase B — Núcleo mecánico

**B1 · Rule Arbiter (v0.4.0)** — `narrator/core/rule_arbiter.py`
El LLM ya no calcula reglas: al enviar una tirada, Python la resuelve contra
la planilla y el narrador recibe el veredicto ya calculado (sección
`RESOLUCIÓN MECÁNICA`, visible en el chat con ⚖). Elimina alucinación numérica.

| Mecánica | Sistemas | Detalle |
|---|---|---|
| `d20_vs_dc` | D&D 5e, PF2e | d20 + modificador vs CD; críticos naturales 20/1 |
| `pool_d10` | VtM V20 | éxitos netos (los 1 restan), botch |
| `percentil` | CoC 7e | normal / duro / extremo / pifia |
| `ratio` | Genérico | bandas PbtA-like 10+ / 7-9 / 6- |

Dificultad determinística: escalera estándar por sistema (YAML `resolution`),
keywords de contexto, u override del jugador ("CD 18").

**B2 · Memoria episódica de 3 capas (v0.5.0)** — `narrator/core/memory_manager.py`

| Capa | Contenido |
|---|---|
| 1 — Working | Últimos 10 mensajes tal cual (antes iba TODO el historial) |
| 2 — Episódica | Turnos viejos resumidos en background a viñetas factuales → sección `MEMORIA DE LA SESIÓN` |
| 3 — Larga duración | RAG semántico sobre el vault (preexistente) |

Persistente entre ejecuciones; robusta ante fallos del LLM (reintenta lotes).

### Fase C — Capa narrativa (v0.6.0)

- **C1 · Psicología de NPCs** (`narrator/core/npc_psyche.py`): arquetipo
  jungiano dominante (12) + rasgos 0–1 (extraversión, amabilidad, neuroticismo,
  impulsividad, agresividad, empatía) en el frontmatter del vault, asignados
  por el extractor y editables en Obsidian. En escena: línea conductual
  `psique: sombra (guarda secretos; desconfiado) — agresividad alta`.
- **C2 · Sistema de Escenas** (`narrator/core/scene_manager.py`): contenido en
  el vault (`tipo: escena`), estado en `estado_campana.yaml`. Desbloqueo
  determinístico por keywords del jugador (`detectar`), flags
  (`requiere_flags`) o reloj lleno (`reloj`); ciclo bloqueada → disponible →
  jugada con `otorga_flags`. Visible en el tab Estado.
- **C3 · Fronts reactivos**: las acciones del jugador aceleran en vivo los
  relojes de frentes sensibles (`reactivo_a` por tipo de evento); un reloj
  llenado en vivo dispara un `EVENTO FORZOSO` que interrumpe la escena en ese
  mismo turno.

### Referencias analizadas

Patrones extraídos (solo lectura) de dos proyectos de referencia:
- *Psyche Simulacra*: arquetipos + rasgos dimensionales (reducidos a lo útil
  para prompts; se descartó ABM/campo colectivo).
- *Panel de Control (La Guerra de la Rabia)*: separación contenido/estado para
  escenas con desbloqueos.

---

## 2. Qué falta por hacer

### Corto plazo

- [ ] **Prueba de juego completa de v0.6.0** con un manual real: reconstruir
  el vault (botón "Vault") para que los NPCs reciban psique y los frentes
  reactividad; crear escenas de ejemplo en Obsidian.
- [ ] **Deuda de lint preexistente**: 64 errores ruff (60 auto-corregibles con
  `--fix`) en código heredado — abrir `fix/lint-ruff`.
- [ ] Afinar keywords de `resolution` en los YAML con experiencia de juego real.

### Mediano plazo (diferidos por decisión, reevaluar tras validar el experimento)

- [ ] **Macros narrativas**: botones de acción que disparen directamente el
  Rule Arbiter (la base ya existe; reduce latencia por turno).
- [ ] **Pipeline de módulos de aventura**: DOCX/XLSX → escenas del vault
  (patrón extractor del Panel de Control).
- [ ] **Transformaciones psicológicas**: deriva de arquetipos por eventos
  (trauma, traición) — v2 de la psicología de NPCs.
- [ ] **Estadísticas narrativas** (Fase 3 del roadmap del README): métricas de
  comportamiento del LLM, uso de movimientos del Máster, evolución de frentes.

### Largo plazo (descartado por ahora — contra la premisa single-user)

- Migración web (NiceGUI / FastAPI + HTMX) — solo si se valida la necesidad
  de tablets/multi-dispositivo.
- Persistencia SQLite — el vault MD/YAML + JSON alcanza para single-user.
- Mapa de zonas (grafo táctico) — versión mínima posible: "zona actual + salidas".
- **Multijugador WebSocket** — descartado: reestructuración completa que no
  sirve al experimento narrativo actual.

---

## 3. Cómo retomar

```bash
# Entorno: conda env con Python 3.11+ (deps: pip install -e ".[semantic,dev]")
# Ollama corriendo con mistral:7b (default de config/config.yaml)
python main.py
```

1. La app guía el inicio: juego → manual PDF → planilla PDF → jugar.
2. Tiradas: panel de dados → "Enviar resultado" → veredicto ⚖ automático.
3. `pytest tests/` → 69 tests; `ruff check narrator/core/` para lo nuevo.

**Últimos merges:** `3a0ce97` (v0.6.0) · historial completo en `CHANGELOG.md`.
