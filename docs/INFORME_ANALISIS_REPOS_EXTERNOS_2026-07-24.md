# Informe — Análisis de repos externos y funcionalidades reconstruibles

**Fecha:** 2026-07-24 · **Alcance:** 7 repos públicos de GitHub, clonados y analizados en profundidad (código real, no solo README) contra la arquitectura actual de AI NARRATOR (`Orchestrator`, `RuleArbiter`, `StateManager`, `PromptBuilder`, `memory_manager`, `npc_psyche`, `theory_engine/`, vault Markdown+YAML).

> Nota metodológica: los repos se clonaron temporalmente fuera del proyecto (carpeta de scratchpad de sesión) solo para lectura/análisis. No se copió código de ellos al repo; este informe es la base para decidir qué reimplementar y con qué alcance.

---

## Resumen ejecutivo

| Repo | Qué es realmente | Licencia | Relevancia para AI NARRATOR |
|---|---|---|---|
| [chdvg/VTT_DND](https://github.com/chdvg/VTT_DND) | VTT (mesa virtual) D&D 5e, Node/WebSockets, mono-servidor local | **MIT** | Media — solo si se agrega modo mapa táctico |
| [Snarfbur/maptool](https://github.com/Snarfbur/maptool) | Mirror/fork sin cambios propios del MapTool oficial de RPTools (Java) | **AGPLv3** | Muy baja — VTT visual pesado, sin IA |
| [Help3D-Padova/Veilforge](https://github.com/Help3D-Padova/Veilforge) | Herramienta de fog-of-war para 2do monitor (PyQt6), sin IA | Licencia propia no comercial | Baja-media — solo si hay mapas |
| [MarquesDeCarabas/vtm-storyteller](https://github.com/MarquesDeCarabas/vtm-storyteller) | Narrador IA de VtM **V5** vía Flask/OpenAI/Discord/Roll20, cloud | Sin licencia declarada | **Alta** — mismo dominio (VtM), varios patrones directos |
| [1A7432/loreweaver](https://github.com/1A7432/loreweaver) | "AI Game Master" self-hosted multiusuario (CoC7e/D&D5e), Python/TUI/p2p | **MIT** | **Muy alta** — arquitectura hermana, incluye harness IA-vs-IA |
| [Kenhito/Marinara-RPG-Extension](https://github.com/Kenhito/Marinara-RPG-Extension) | Overlay de reglas agnóstico para Marinara Engine (frontend tipo SillyTavern) | **MIT** (contenido de sistemas con licencias propias) | Alta — taxonomía de reglas y protocolo de tags de estado |
| [SethCWilliams/ttrpg-dm-toolkit](https://github.com/SethCWilliams/ttrpg-dm-toolkit) | Toolkit web de gestión de campaña (FastAPI+SvelteKit), IA solo para NPCs | **MIT** | Media-alta — patrones de generación IA y entidades de mundo que nos faltan |

**Los tres repos más valiosos, en orden: `loreweaver` > `vtm-storyteller` > `Marinara-RPG-Extension` / `ttrpg-dm-toolkit`.** `maptool` y `Veilforge` solo aportan si en algún momento se agrega un mapa visual (hoy fuera de alcance: AI NARRATOR es narrativo-textual). `VTT_DND` aporta ideas puntuales de bajo esfuerzo.

**Aviso de licencias:** `maptool` (AGPLv3) y `Veilforge` (no comercial) **no deben copiarse textualmente** — solo sirven como referencia conceptual para reimplementación propia ("clean-room"). `vtm-storyteller` no declara licencia (default: todos los derechos reservados) — tratarlo también como referencia de patrones, no como fuente de código a copiar. Los MIT (`VTT_DND`, `loreweaver`, `Marinara-RPG-Extension`, `ttrpg-dm-toolkit`) permiten adaptación más directa, siempre y cuando se mantenga sentido crítico sobre si conviene portar código o solo la idea (nuestro stack es Python/Dear PyGui, la mayoría de estos son Node/Java/Flask/TS).

---

## 1. Implementaciones reconstruibles — priorizadas por valor/esfuerzo

### Prioridad alta (impacto directo en el "principio fundamental": Python decide, LLM narra)

| # | Implementación | Origen | Esfuerzo | Qué resuelve |
|---|---|---|---|---|
| 1 | **Harness IA-vs-IA con gate cuantitativo** (arquetipos de jugador simulados + métricas de fuga de secretos + "tirada antes de narrar" + exit code para CI) | `loreweaver/scripts/playtest.py` | Medio-alto | Es literalmente la **Fase 4 del roadmap** ("IA vs IA"), hoy sin ningún código. Este patrón es adaptable casi 1:1. |
| 2 | **DSL seguro para stats derivados en YAML** (`copy_of`, `half_of`, `floor_div`, `sum_ranges`, `computer` registrado por nombre) — reemplaza cualquier fórmula ad-hoc | `loreweaver/core/rulepacks.py` | Bajo | Robustece `data/systems/*.yaml` sin introducir `eval()`; separa datos de cómputo, coherente con la filosofía del `RuleArbiter`. |
| 3 | **Auto-detección y guardado de entidades desde texto del LLM** (etiquetas `NAME:`/`CLAN:`/`ATTRIBUTES:` parseadas a Markdown+YAML del vault sin comando explícito) | `vtm-storyteller/campaign_auto_save.py` | Medio | Automatiza lo que hoy exige "pedile explícitamente que guarde en JSON" (limitación documentada en nuestro propio README). |
| 4 | **Recall por menciones en el mensaje del jugador** (detectar verbo de acción + nombre propio → disparar búsqueda en vault solo si es relevante) | `vtm-storyteller/campaign_ai_integration.py` | Bajo-medio | Complementa el `VaultRetriever` actual con contexto activado por keyword, más barato que RAG completo. |
| 5 | **Actores de NPC con contexto aislado estructuralmente** (system prompt de cada NPC construido *solo* desde su propio registro, nunca desde el pool del Máster) | `loreweaver/agent/npc_actor.py` | Medio | Previene fugas de Misterios/secretos vía diálogo de NPC — refuerza `npc_psyche.py` y el `InvestigationEngine`. |
| 6 | **Regla "dice-first" como detector estructural** (heurística: ¿la acción requería tirada? ¿el LLM narró resultado sin tirar? corrección acotada) | `loreweaver/agent/loop.py` | Medio | Formaliza en código el principio "RuleArbiter resuelve, LLM narra" — hoy depende solo de instrucción en el prompt. |
| 7 | **Parser de comando "tirada sugerida pendiente"** (LLM sugiere "tirá Fuerza+Pelea", se extrae por regex, usuario confirma con un click sin retipear) | `vtm-storyteller/intelligent_dice_system.py` | Bajo | Reduce fricción de UX en el panel de dados de `app.py`; encaja directo con el `RuleArbiter`. |
| 8 | **Protocolo de tags inline de mutación de estado** (`[state: field=hp delta=-3 reason=...]` al final del párrafo narrado, parseado y aplicado) | `Marinara-RPG-Extension` | Medio | Alternativa barata a una llamada extra de extracción JSON — aplica a HP/condiciones/inventario en la ficha. |

### Prioridad media (enriquecen el modelo de datos / robustez)

| # | Implementación | Origen | Esfuerzo | Qué resuelve |
|---|---|---|---|---|
| 9 | **Entidad "Organizaciones/Facciones"** (goals, methods, resources, influence, alianzas/enemistades) | `ttrpg-dm-toolkit` | Medio | Hoy el vault no modela facciones como entidad propia más allá de "Cofradías" — completa el esquema. |
| 10 | **Entidad "Eventos"** con timeline causa-efecto (histórico/actual/programado) | `ttrpg-dm-toolkit` | Medio | Complementa memoria episódica como "historia del mundo" persistente fuera de sesiones. |
| 11 | **Field-locking en generación de NPCs** (fijar campos elegidos, regenerar el resto vía LLM) | `ttrpg-dm-toolkit` | Bajo | Mejora `ExtractorAgent`/edición manual de NPCs en Obsidian. |
| 12 | **Reparación robusta de JSON malformado del LLM** (balanceo de llaves, saneo de campos numéricos, reintento con fallback a plantilla) | `ttrpg-dm-toolkit/npc_generator.py` | Bajo | Directamente aplicable a `sheet_parser.py`, `ExtractorAgent` y cualquier parseo de JSON embebido en respuestas de Ollama. |
| 13 | **Factory multi-proveedor con Ollama first-class** (`PRESETS` + detección de base_url, con Ollama como default sin credenciales) | `loreweaver/infra/providers.py` | Bajo | Prepara el terreno por si algún día se quiere permitir un modelo más potente como fallback, sin romper el modo 100% local. |
| 14 | **`@tool` decorator con schema generado desde type hints + docstring**, con flags `keeper_only`/`gated` | `loreweaver/agent/tools.py` | Bajo-medio | Si se migra de prompts monolíticos a function-calling, formaliza qué puede ver/hacer el LLM vs el `RuleArbiter`. |
| 15 | **Taxonomía formal de "modos de resolución"** (single-roll, dice-pool, d100, 2d6-band, roll-under...) validada por schema | `Marinara-RPG-Extension/schema/ruleset.schema.json` | Medio | Formaliza y valida `resolution:` en los YAML de sistema antes de que el `RuleArbiter` los consuma. |
| 16 | **Lorebook keyword-triggered (position + tokenBudget)** como RAG liviano sin embeddings | `Marinara-RPG-Extension` | Bajo | Alternativa/complemento al `Embedder` actual para reglas específicas de sistema, sin depender de `nomic-embed-text`. |
| 17 | **Ideas Inbox** (`raw_idea → developing → ready_to_implement → implemented`) como bandeja de borradores antes de materializar en el vault | `ttrpg-dm-toolkit` | Bajo | Encaja con el flujo Obsidian: notas sueltas en `Notas/` con estado, antes de promover a NPC/Locación formal. |
| 18 | **Deduplicación semántica de eventos de sesión** (evita registrar el mismo hito narrativo dos veces con distinta redacción) | `loreweaver/agent/loop.py` | Medio | Mejora la memoria episódica (capa 2) evitando resúmenes redundantes. |
| 19 | **Extracción de fichas PDF vía campos AcroForm** (`PyPDF2.get_fields()`) como vía alternativa cuando el PDF es rellenable oficial | `vtm-storyteller/pdf_character_parser.py` | Medio | Complementa `sheet_parser.py` (hoy solo extracción de texto vía LLM) con un camino más robusto para PDFs con formulario. |

### Prioridad baja / opcional (requieren evaluar si entran en el alcance del proyecto)

| # | Implementación | Origen | Esfuerzo | Nota |
|---|---|---|---|---|
| 20 | Narración por voz local (TTS) con toggle + reproducción async | Idea de `vtm-storyteller/VOICE_NARRATION.md` (implementación real es cloud/ElevenLabs, no portable) | Alto | Requeriría Piper/Coqui/pyttsx3 local; evaluar calidad/latencia antes de comprometerse. |
| 21 | Import/export de NPCs como SillyTavern V2 character card (PNG con chunk `chara`) | `Marinara-RPG-Extension` | Medio-alto | Interoperabilidad con ecosistema externo; nicho, solo si se busca compatibilidad comunitaria. |
| 22 | Modelo de token con metadata rica + fog-of-war como grid booleano serializable | `VTT_DND` | Bajo-medio | Solo aplica si se agrega un modo de mapa táctico (hoy no está en el roadmap). |
| 23 | Pincel de fog-of-war con feathering (gradiente radial) + suavizado de trazos Chaikin | `Veilforge` | Medio / Bajo | Ídem — solo con mapas visuales. Licencia no comercial: reimplementar desde cero, no copiar. |
| 24 | Máquina de estado de iniciativa/combate con targeting (`InitiativeList`) | `VTT_DND` / `maptool` | Bajo | Útil solo si se decide modelar combate por turnos explícito (hoy resuelto de forma narrativa vía `RuleArbiter`). |
| 25 | Búsqueda global cross-entidad sobre el vault (tipo full-text simple) | `ttrpg-dm-toolkit` | Medio | Utilidad de conveniencia para navegar el vault durante sesión, no crítica. |

---

## 2. Descartado explícitamente (para que quede registrado por qué no se persigue)

- **`maptool`**: es esencialmente un mirror sin cambios propios del MapTool oficial (Java/Swing, AGPLv3, multiusuario en red, fog-of-war/pathfinding geométrico pesado). Cero integración de IA. Fuera del alcance narrativo-textual de AI NARRATOR; no vale la pena invertir tiempo salvo el concepto puntual de cola de iniciativa (ítem #24).
- **Networking multiusuario (WebSockets/broadcast) de `VTT_DND` y `loreweaver`**: irrelevante — AI NARRATOR es mono-usuario por decisión de diseño explícita (ver `ROADMAP.md`: "Multijugador WebSocket — descartado").
- **Capa Flask/SQLite completa de `vtm-storyteller`**, `discord_bot.py`, `roll20_integration.py`: arquitectura cloud multi-usuario incompatible con el enfoque local/vault-first; además el código de persistencia tiene SQL crudo con f-strings (riesgo de inyección) que no conviene ni como referencia de implementación.
- **Sistema de dados V5 de `vtm-storyteller`**: es VtM 5ª edición (hunger dice, mecánica de éxito a 6+), mientras nuestro `pool_d10` es V20 — mecánicas distintas. Solo sirve como referencia si algún día se agrega V5 como sexto sistema soportado.

---

## 3. Sugerencia de secuencia (si se aprueba avanzar)

No se ejecuta nada de esto sin roadmap aprobado — se deja listo para decidir en la próxima sesión de trabajo:

1. **Quick wins de bajo esfuerzo y alto ratio valor/riesgo** (ítems 2, 4, 7, 12, 13, 17): tocan `RuleArbiter`, `retriever.py`, `sheet_parser.py`, `llm_client.py` — cambios acotados, sin romper arquitectura existente.
2. **Automatización de vault** (ítems 3, 8, 18): mayor impacto en la experiencia de juego (menos intervención manual del usuario), pero tocan `VaultWriter`/`memory_manager` — requiere más pruebas.
3. **Enriquecimiento de esquema** (ítems 9, 10): decisión de diseño sobre el modelo del vault, ideal para tratar junto con los ítems ya diferidos del `PLAN_FIXES_20260702.md` (conectar `InvestigationEngine`/`WorldSimulationEngine` al flujo real).
4. **Fase 4 del roadmap (IA-vs-IA)**: el ítem #1 (harness de `loreweaver`) es la pieza más grande y más alineada con algo que ya está planificado pero no iniciado — candidato a su propio roadmap de sesión dedicado.

---

*Repos clonados temporalmente en directorio de scratchpad de sesión para este análisis; no se incorporó código de terceros al repositorio. Este archivo es el único artefacto persistente del análisis.*
