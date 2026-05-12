# NARRADOR — Roadmap de Desarrollo
> Este archivo es memoria de sesión. Claude lo lee y actualiza en cada sesión para mantener coherencia.

---

## Visión del Proyecto

Sistema narrador de TTRPG impulsado por LLMs locales (Ollama). Un ecosistema de agentes especializados que mantienen la coherencia del mundo mientras un modelo pequeño (7B) narra las escenas.

**Principio fundamental:** El LLM es el pincel, no el cerebro. El sistema mantiene la coherencia; el modelo solo pinta las escenas.

**Constraint técnico clave:** Modelos 7B tienen ~2000 palabras de contexto útil. Cada agente recibe SOLO el fragmento del vault que necesita.

---

## Fases

### FASE 1 — Narrador con Jugador Humano
Usuario carga manual PDF → agentes construyen mundo/NPCs/trama → IA guía creación de personaje → IA narra la crónica

### FASE 2 — IA vs IA (Investigación Científica)
Reemplazar jugador humano con otra IA. Historia narrada por una IA, jugada por otra. Investigación de storytelling emergente entre LLMs.

---

## Arquitectura

```
PDF → [Extractor] → VAULT (MD/YAML)
                         ↓
              [Orquestador — Python puro]
              /           |           \
    [Narrador]    [Mundo/Relojes]  [Rutinas NPC]
         ↓               ↓               ↓
    GUI (Dear PyGui) ← estado ← vault_context
```

---

## Sistemas Soportados

| Sistema | Archivo | Estado |
|---------|---------|--------|
| Vampiro: La Mascarada V20 | `systems/vtm_v20.yaml` | ✅ Completo |
| Dungeons & Dragons 5e | `systems/dnd_5e.yaml` | ✅ Completo |
| La Llamada de Cthulhu 7e | `systems/coc_7e.yaml` | ✅ Completo |
| Pathfinder 2e | `systems/pathfinder_2e.yaml` | ✅ Completo |
| Genérico | `systems/generic.yaml` | ✅ Completo |

---

## Estado Actual del Código

### ✅ Completado
- `narrator.py` — GUI funcional (Dear PyGui) + integración Ollama + carga PDF + dados + botón "Construir Vault"
- `systems/*.yaml` — VtM V20, D&D 5e, CoC 7e, Pathfinder 2e, Generic — todos con `npc_acciones`
- `vault_template/` — Estructura de carpetas para vault de campaña (compatible Obsidian)
- `estado_campana.yaml` — Esquema de estado de campaña
- `config.yaml` — Configuración global
- `Prompt_Generador_Cronica.md` — Pipeline de 8 fases para worldbuilding desde sourcebook
- `README.md` — Unificado (eliminado README (2).md)
- `core/llm_client.py` — Wrapper Ollama (streaming + sync)
- `core/retriever.py` — Búsqueda en vault por tipo/keyword
- `core/state_manager.py` — Gestión de estado_campana.yaml (relojes, flags, escenas)
- `core/prompt_builder.py` — Ensamblado de prompts desde system YAML + vault
- `agents/orchestrator.py` — Orquestador central (Python puro, sin LLM)
- `agents/extractor_agent.py` — Pipeline PDF → vault (extracción NPCs/Locaciones/Facciones + generación Frentes + Dashboard)
- `agents/narrator_agent.py` — Detección de tiradas/JSON en respuestas
- `agents/npc_routines.py` — Simulación de comportamiento de NPCs con action pools
- `.gitignore` — Actualizado (vault/, estado_campana.yaml, .claude/, *.docx)

### 🔲 Pendiente — Sprint 3
- [ ] Búsqueda semántica en retriever (ChromaDB o nomic-embed-text via Ollama)
- [ ] Soporte multi-PDF (manual base + suplementos)
- [ ] Panel de estado de campaña en GUI (relojes de frentes visibles)
- [ ] Exportar log de sesión como Markdown/PDF

### ✅ Obsidian — Live updates implementados
- `core/vault_writer.py` — escribe al vault durante la sesión
  - Log de sesión en `vault/Sesiones/Sesion_N.md` por cada intercambio
  - Notas de NPCs actualizadas automáticamente cuando aparecen en respuestas
  - Notas de locaciones cuando se mencionan en la narrativa
  - Tiradas de dados registradas con timestamp
- Activar/desactivar con `vault.live_updates` en `config.yaml`
- Obsidian detecta los cambios de archivo automáticamente (live reload nativo)

### 🔲 Pendiente — Sprint 3
- [ ] `agents/world_agent.py` — Avance autónomo del mundo entre sesiones (relojes, downtime NPC)
- [ ] Panel de estado de campaña en la GUI (relojes, frentes activos)
- [ ] Exportar log de sesión
- [ ] Editor de hoja de personaje manual en GUI

### 🔲 Pendiente — Fase 2 (Investigación)
- [ ] `agents/player_agent.py` — IA jugadora que recibe escena y devuelve acción
- [ ] Loop autónomo narrador/jugador
- [ ] Sistema de métricas de coherencia narrativa

---

## Decisiones de Diseño Tomadas

1. **El orquestador es Python puro** — no un LLM. Decide qué agente llama y con qué contexto mínimo.
2. **El vault son archivos MD/YAML** — memoria compartida entre agentes, persistente entre sesiones.
3. **narrator.py mantiene la GUI** — solo cambia el backend de contexto. Backward compatible.
4. **Fallback graceful** — si los agentes no están disponibles, narrator.py cae back al modo legacy.
5. **GitHub**: no todavía, agregar más adelante cuando Marcos lo indique.

---

## Notas de Sesión

### Sesión 2026-05-11 (parte 1)
- Análisis completo: fusión narrator.py + arquitectura vault/agentes
- Implementado: core/ + agents/ (sin extractor)
- Refactorizado: narrator.py con orquestador + fallback graceful
- Agregado: pathfinder_2e.yaml, npc_acciones en todos los sistemas

### Sesión 2026-05-11 (parte 2)
- README unificado (eliminado README (2).md duplicado)
- Implementado: agents/extractor_agent.py — pipeline completo PDF → vault
- Integrado botón "Construir Vault" en GUI
- Implementado: core/vault_writer.py — vault en tiempo real (Obsidian live reload)
- Repo GitHub creado: https://github.com/martinezmarcos93/AI_NARRATOR.git
- Pusheados dos commits (initial + vault_writer)
- Pendiente para próxima sesión: Sprint 3 (búsqueda semántica, panel relojes en GUI)
