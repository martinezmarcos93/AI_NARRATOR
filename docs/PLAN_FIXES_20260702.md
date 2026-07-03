# Plan de Fixes — Auditoría 2026-07-02

> **NOTA DE CONTINUACIÓN (para Claude o quien retome):**
> Rama: `fix/auditoria-20260702` (creada desde `main` local `d3a60a1`).
> **El `git log` de esta rama ES el estado real** — cada fix es un commit atómico
> `fix(...): PX-N descripción`. Lo pendiente = ítems de abajo sin commit correspondiente.
> Protocolo: un commit por fix → push inmediato a `origin/fix/auditoria-20260702`.
> El informe completo de auditoría con file:line está en la conversación que originó
> esta rama; este archivo resume lo accionable.
> ⚠ OJO: `main` local diverge de `origin/main` (2↑/1↓, conflicto real en `app.py`
> con el commit remoto `5455e46`). NO resolver sin Marcos. Esta rama nace del main LOCAL.

## P0 — Crítico (GUI)

- [ ] **P0-1** `app.py:276-286` — `section_label`/`dim_text` usan `dpg.add_text(label=...)` → texto invisible (verificado: value=''). Pasar el texto como primer posicional.
- [ ] **P0-2** `app.py:1170-1172` — `build_dice_panel(dpg.last_item())` recibe el spacer como parent. Usar `with dpg.tab(...) as tab_dados:`.
- [ ] **P0-3** `app.py:1244` — `callback=send_message` recibe sender → envía "send_btn" como mensaje. Ídem `app.py:1264` `callback=export_session_log` → `silent=sender` truthy. Envolver en lambdas sin args.
- [ ] **P0-4** `app.py:1358-1364` — excepción en lambda encolado mata el render loop (solo captura `queue.Empty`). try/except alrededor de `fn()`.
- [ ] **P0-5** `app.py:1273-1286` — "Nueva sesión" borra `streaming_group` (vive dentro de `chat_scroll`) → próximo mensaje crashea vía P0-4. Extraer `new_session_callback()` que recree el grupo; `move_item` del streaming group al final del chat en cada envío; resetear `pacing_agent`.

## P1 — Alto

- [ ] **P1-2** Banda de tirada: `do_roll` guarda `state["tirada_banda"]` ('10+'/'7-9'/'6-' por ratio total/máximo ≥0.8/≥0.5); `orchestrator._build_move_context` la lee (hoy lee `last_dice_result` ya consumido → siempre None). Limpiar tras armar contexto.
- [ ] **P1-3** `app.py:410-415` — `get_context_for_phase` (IO vault + HTTP embeddings) corre en el hilo de la GUI. Moverlo al worker `run()`.
- [ ] **P1-4** Sesión restaurada invisible: re-render de chat/hoja/log tras `build_gui()`; persistir `session_number` en `session_manager.py`.
- [ ] **P1-5** Triple contabilidad de relojes: en `run_world_agent`, sincronizar StateManager (`add_front`+`advance_front_clock`) y WorldSim (`initialize_front`+`advance_front`) — hoy ambas llamadas son no-ops.
- [ ] **P1-6** `llm_client.py` — chequear status HTTP y clave `error` de Ollama en streaming; en `app.finish_streaming`, NO agregar respuestas `[Error...]` al historial (mostrarlas como sistema).
- [ ] **P1-7** `extract_pdf_text` devuelve el error como texto → "✓" falso. Devolver None y notificar en GUI (también en suplementos).
- [ ] **P1-8** Rutas relativas al CWD (`orchestrator.py:21-23`): anclar a `PROJECT_ROOT`. `app.py` (build_vault, export, init_vault_writer) usa las rutas resueltas del orchestrator.
- [ ] **P1-9** Cache stale: `retriever.invalidate_cache()` (índice + disponibilidad embedder) llamado tras construir el vault.
- [ ] **P1-10** `state_manager.load`: YAML corrupto → backup `.corrupto-TIMESTAMP` + log ruidoso (hoy lo pisa en silencio).

## P2 — Quick wins incluidos

- [ ] **P2-a** D100 en `DICE_TYPES` (CoC 7e es percentil).
- [ ] **P2-b** Engines: quitar `logging.basicConfig` (side effect global en import) y el shadowing del logger central en los 4 módulos de theory_engine; limpiar `import json` interno en `investigation_engine._save_state`.
- [ ] **P2-c** `retriever.get_fronts_with_clocks`: regex `\[.\]` cuenta falsos ticks → contar solo `[ ]` y `[x]`.
- [ ] **P2-d** `vault_writer`: backlink `[[Sesion_XX]]` roto → usar el stem real del archivo de sesión.

## P2 — Diferidos (necesitan decisión de diseño / no tocar sin Marcos)

- Conectar InvestigationEngine (nadie llama `register_mystery`) y WorldSim al flujo real (P1-1) — feature, no fix.
- Código muerto: `NPCRoutinesAgent`, `update_dashboard_state`, flags/escena de StateManager, etc.
- Unificar los dos `detect_system`; unificar exportadores de sesión.
- Layout no responsive al redimensionar viewport.
- Mensajes de log genéricos ("Error inesperado") — pase global de mensajes específicos.
- Divergencia main/origin (decisión de Marcos).
