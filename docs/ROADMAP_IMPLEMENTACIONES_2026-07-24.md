# Roadmap maestro — Implementaciones desde repos externos (2026-07-24)

> Deriva de `docs/INFORME_ANALISIS_REPOS_EXTERNOS_2026-07-24.md`. Cubre las 25 implementaciones
> identificadas, agrupadas en **22 fases** (una rama por fase), ordenadas de **menor a mayor
> complejidad** según lo pedido. Cada fase sigue el ciclo estándar: rama desde `main` actualizada →
> desarrollo → tests/verificación → commit atómico notificado → merge solo con aprobación explícita.
>
> **Nada se ejecuta sin aprobación de esta propuesta.** Una vez aprobada, se trabaja fase por fase,
> en el orden dado, verificando cada una antes de pasar a la siguiente (no se abren varias ramas en
> paralelo salvo que se indique lo contrario).

---

## Cómo leer cada fase

- **Rama:** nombre sugerido (`feature/<nombre>`).
- **Complejidad:** bajo / bajo-medio / medio / medio-alto / alto (según el informe).
- **Objetivo:** qué problema resuelve, en una frase.
- **Pasos:** numerados, concretos.
- **Archivos involucrados:** los que se tocan o crean.
- **Criterios de aceptación:** cómo se verifica que la fase está "hecha" (tests, comportamiento observable).

---

## BLOQUE 1 — Complejidad BAJA (fases 1 a 7)

### Fase 1 — DSL seguro para stats derivados
**Rama:** `feature/dsl-reglas-derivadas` · **Complejidad:** bajo · **Origen:** loreweaver (#2)

**Objetivo:** eliminar cualquier fórmula ad-hoc/implícita en los YAML de sistema, reemplazándola por un vocabulario fijo y seguro (`copy_of`, `half_of`, `floor_div`, `sum_ranges`, `computer` registrado por nombre) para calcular estadísticas derivadas, sin usar `eval()`/`exec()`.

**Pasos:**
1. Definir el vocabulario mínimo necesario revisando qué estadísticas derivadas ya calculan los 5 YAML de sistema (`data/systems/*.yaml`) de forma implícita hoy (si las hay) o cuáles necesitaría el `RuleArbiter` a futuro.
2. Implementar `narrator/core/derived_stats.py` con el compilador/evaluador del DSL (funciones puras registradas en un dict `{"copy_of": ..., "half_of": ..., ...}`).
3. Añadir bloque `derived:` opcional en el schema de `data/systems/*.yaml` donde aplique (ej. modificador de atributo en D&D5e).
4. Integrar la evaluación en `PromptBuilder`/`RuleArbiter` donde se necesiten esos valores.
5. Tests unitarios de cada función del DSL + casos de error (clave desconocida → excepción clara, nunca fallo silencioso).

**Archivos:** `narrator/core/derived_stats.py` (nuevo), `data/systems/*.yaml`, `narrator/core/rule_arbiter.py`, `tests/test_derived_stats.py` (nuevo).

**Criterios de aceptación:** tests nuevos en verde, ningún `eval`/`exec` introducido, `pytest tests/` completo sigue en verde.

---

### Fase 2 — Tirada sugerida pendiente
**Rama:** `feature/tirada-sugerida` · **Complejidad:** bajo · **Origen:** vtm-storyteller (#7)

**Objetivo:** cuando el narrador sugiere una tirada en su narración ("tirá Fuerza + Pelea"), extraerla y guardarla como "pendiente" para que el jugador la confirme con un click en vez de reconfigurar el panel de dados a mano.

**Pasos:**
1. Regex de extracción de sugerencia de tirada sobre la respuesta del narrador (atributo/habilidad mencionados, dificultad si aparece explícita).
2. Guardar en `app_state["tirada_sugerida"]` (o similar) tras cada `finish_streaming`.
3. En el panel de dados de `app.py`, mostrar la sugerencia si existe y agregar botón "Usar sugerida" que precargue el tipo/cantidad de dado.
4. Limpiar la sugerencia una vez usada o al iniciar un nuevo turno.

**Archivos:** `narrator/agents/narrator_agent.py` (extracción), `narrator/app.py` (UI del panel de dados).

**Criterios de aceptación:** test unitario de la regex con casos variados (con/sin dificultad explícita, distintos sistemas); verificación manual en GUI de que el botón aparece y precarga correctamente.

---

### Fase 3 — Robustez de generación de NPCs (field-locking + JSON reparado)
**Rama:** `feature/npc-gen-robustez` · **Complejidad:** bajo · **Origen:** ttrpg-dm-toolkit (#11, #12)

**Objetivo:** (a) permitir fijar campos elegidos por el usuario al regenerar un NPC vía LLM, sin perderlos; (b) reparar JSON malformado devuelto por el LLM en vez de descartarlo.

**Pasos:**
1. `narrator/core/json_repair.py` (nuevo): balanceo de llaves faltantes, saneo de campos numéricos con texto embebido, reintento controlado, fallback a plantilla mínima si falla dos veces.
2. Integrar `json_repair` en todos los puntos que ya parsean JSON del LLM: `sheet_parser.py`, `extractor_agent.py`, `narrator_agent.py`.
3. Agregar parámetro `locked_fields: dict` a la función de generación/regeneración de NPCs en `extractor_agent.py`; el prompt indica explícitamente "no modifiques estos campos: {locked_fields}".
4. Tests con salidas de LLM deliberadamente rotas (llave faltante, coma final, número con texto).

**Archivos:** `narrator/core/json_repair.py` (nuevo), `narrator/core/sheet_parser.py`, `narrator/agents/extractor_agent.py`, `narrator/agents/narrator_agent.py`, `tests/test_json_repair.py` (nuevo).

**Criterios de aceptación:** tests de reparación en verde para al menos 5 casos de corrupción distintos; parseo existente (`sheet_parser`, extractor) sigue pasando sus tests actuales.

---

### Fase 4 — Factory multi-proveedor con Ollama first-class
**Rama:** `feature/llm-provider-factory` · **Complejidad:** bajo · **Origen:** loreweaver (#13)

**Objetivo:** preparar `llm_client.py` para soportar más de un backend (Ollama por defecto sin credenciales, con posibilidad de fallback a otro modelo Ollama o proveedor compatible OpenAI-API) sin romper el modo 100% local actual.

**Pasos:**
1. Definir `AIProvider` como clase base mínima (`chat`, `stream_chat`, `is_available`).
2. Refactorizar `LLMClient` actual como implementación `OllamaProvider`.
3. `ProviderFactory` con `PRESETS` (`ollama` por defecto) y detección de `base_url` en `config/config.yaml`.
4. Sin cambiar el comportamiento por defecto: config actual sigue funcionando idéntico sin tocar `config.yaml`.

**Archivos:** `narrator/core/llm_client.py` (refactor), `narrator/core/providers.py` (nuevo, opcional según cuánto se quiera separar), `config/config.yaml` (documentar nueva clave opcional).

**Criterios de aceptación:** app arranca y juega un turno completo sin cambios de configuración; tests existentes de integración con `llm_client` (si los hay) siguen en verde.

---

### Fase 5 — Lorebook por keywords (RAG liviano)
**Rama:** `feature/lorebook-keywords` · **Complejidad:** bajo · **Origen:** Marinara-RPG-Extension (#16)

**Objetivo:** inyectar reglas/notas específicas del sistema activo cuando el texto del jugador/narrador contiene ciertas keywords, sin depender de embeddings (útil cuando `nomic-embed-text` no está instalado).

**Pasos:**
1. Definir estructura `lorebook:` opcional en `data/systems/*.yaml` (entradas con `keywords`, `content`, `position`, `token_budget` opcional).
2. `narrator/core/lorebook.py` (nuevo): matching simple de keywords sobre el último mensaje, orden por prioridad, recorte a presupuesto de palabras.
3. Integrar como fuente adicional (fallback o complemento) en `VaultRetriever.get_relevant_context` cuando la búsqueda semántica no está disponible.
4. Tests con un lorebook de ejemplo y distintos mensajes de entrada.

**Archivos:** `narrator/core/lorebook.py` (nuevo), `narrator/core/retriever.py`, `data/systems/*.yaml` (campo opcional), `tests/test_lorebook.py` (nuevo).

**Criterios de aceptación:** con embeddings desactivados, el contexto inyectado incluye la entrada de lorebook esperada para un mensaje de prueba con keyword conocida.

---

### Fase 6 — Ideas Inbox
**Rama:** `feature/ideas-inbox` · **Complejidad:** bajo · **Origen:** ttrpg-dm-toolkit (#17)

**Objetivo:** bandeja de borradores (`Notas/` del vault) con estado `raw_idea → developing → ready_to_implement → implemented`, para anotar ideas sueltas antes de convertirlas en NPC/Locación/Frente formal.

**Pasos:**
1. Definir frontmatter mínimo para notas de tipo `idea` (`tipo: idea`, `estado`, `prioridad`, `notas`).
2. Función en `vault_writer.py` o nuevo módulo pequeño para crear/actualizar notas de idea.
3. UI mínima en `app.py` (tab o sección existente) para listar ideas por estado y promoverlas a entidad formal (llamando al flujo de creación de NPC/Locación existente).
4. Test de creación/transición de estado de una idea.

**Archivos:** `narrator/core/vault_writer.py`, `narrator/app.py`, `data/vault_template/Notas/` (ya existe la carpeta), `tests/test_vault_writer.py` (extender si existe, o nuevo).

**Criterios de aceptación:** crear una idea, cambiarla de estado y promoverla genera los archivos esperados en `vault/Notas/` y, al promover, el archivo formal correspondiente.

---

### Fase 7 — Cola de iniciativa/combate con targeting
**Rama:** `feature/iniciativa-turnos` · **Complejidad:** bajo · **Origen:** VTT_DND / maptool (#24)

**Objetivo:** modelo simple de cola de iniciativa (agregar/quitar combatiente, orden, "activo/siguiente", registro de quién ataca a quién) como estructura de datos en Python puro, para combates narrados por turnos explícitos.

**Pasos:**
1. `narrator/core/initiative.py` (nuevo): clase `InitiativeQueue` (add/remove/sort/next/current) y `AttackLog` simple.
2. Integrar en `StateManager` como sub-estado opcional de la escena actual (`escena_actual.combate`).
3. Sección opcional en el prompt (`PromptBuilder`) que informa el orden de turno activo cuando hay combate en curso.
4. Tests de la cola (orden correcto, rotación, remoción de combatiente caído).

**Archivos:** `narrator/core/initiative.py` (nuevo), `narrator/core/state_manager.py`, `narrator/core/prompt_builder.py`, `tests/test_initiative.py` (nuevo).

**Criterios de aceptación:** tests de la cola en verde; el narrador recibe correctamente "es el turno de X" en el prompt cuando hay combate activo.

---

## BLOQUE 2 — Complejidad BAJO-MEDIA (fases 8 a 9)

### Fase 8 — Metadata de NPC/token + recall por mención
**Rama:** `feature/npc-metadata-recall` · **Complejidad:** bajo-medio · **Origen:** VTT_DND (#22) + vtm-storyteller (#4)

**Objetivo:** (a) enriquecer el frontmatter de NPC con metadata de presentación (color/ícono/estado vivo-muerto-KO/condiciones apilables), útil tanto para UI actual como para un futuro modo visual; (b) detectar menciones de NPCs/locaciones en el mensaje del jugador (verbo de acción + nombre propio) y disparar recall automático en el vault sin comando explícito.

**Pasos:**
1. Extender frontmatter de NPC en `extractor_agent.py` con campos `color`, `icono`, `estado` (vivo/muerto/ko), `condiciones: []`.
2. `narrator/core/mention_detector.py` (nuevo): regex de verbo de acción + nombre propio capitalizado, normalización básica.
3. Integrar en `Orchestrator.build_narrator_context`: si hay mención detectada, forzar `retriever.get_relevant_context` sobre esa entidad puntual además del contexto habitual.
4. Tests de detección de menciones (casos positivos/negativos en español).

**Archivos:** `narrator/agents/extractor_agent.py`, `narrator/core/mention_detector.py` (nuevo), `narrator/agents/orchestrator.py`, `tests/test_mention_detector.py` (nuevo).

**Criterios de aceptación:** tests de detección en verde; con un NPC conocido mencionado explícitamente, el contexto del narrador incluye su ficha aunque no sea top-match de la búsqueda semántica general.

---

### Fase 9 — `@tool` decorator con schema tipado
**Rama:** `feature/tool-decorator` · **Complejidad:** bajo-medio · **Origen:** loreweaver (#14)

**Objetivo:** decorador que genera schema de function-calling desde type hints + docstring de una función Python, con flags `keeper_only` (solo visible al motor, no al LLM narrador) y `gated` (requiere condición previa) — sienta la base para migrar de prompts monolíticos a herramientas explícitas si se decide en el futuro.

**Pasos:**
1. `narrator/core/tools.py` (nuevo): decorador `@tool(keeper_only=False, gated=None)` que introspecciona la función y genera un dict de schema JSON.
2. Registrar 1-2 herramientas de ejemplo no críticas (p. ej. "consultar reloj de un frente") para validar el patrón end-to-end, sin cambiar el flujo de prompting actual todavía.
3. Tests de generación de schema desde funciones de ejemplo con distintos tipos (str, int, Optional, list).

**Archivos:** `narrator/core/tools.py` (nuevo), `tests/test_tools.py` (nuevo).

**Criterios de aceptación:** tests en verde; esta fase es infraestructura pura, no debe alterar el comportamiento actual del narrador (no se conecta a `Orchestrator` todavía — eso queda para una decisión de diseño posterior).

---

## BLOQUE 3 — Complejidad MEDIA (fases 10 a 18)

### Fase 10 — Taxonomía y validación de modos de resolución
**Rama:** `feature/taxonomia-resolucion` · **Complejidad:** medio · **Origen:** Marinara-RPG-Extension (#15)

**Objetivo:** formalizar los modos de resolución de dados (`d20_vs_dc`, `pool_d10`, `percentil`, `ratio`, y dejar preparado para futuros como `2d6-band`) como un schema validado, para detectar YAML de sistema mal formado antes de que llegue al `RuleArbiter` en tiempo de juego.

**Pasos:**
1. Definir schema (Pydantic o `jsonschema`) para el bloque `resolution:` de `data/systems/*.yaml`, uno por modo soportado.
2. Validación al cargar cada sistema en `PromptBuilder.load_system` / `RuleArbiter`, con mensajes de error claros (`path/esperado/recibido`).
3. Validar los 5 YAML existentes contra el nuevo schema y corregir cualquier inconsistencia que aparezca.
4. Tests: YAML válido pasa, YAML con campo faltante/tipo incorrecto falla con mensaje claro.

**Archivos:** `narrator/core/resolution_schema.py` (nuevo), `narrator/core/rule_arbiter.py`, `narrator/core/prompt_builder.py`, `data/systems/*.yaml` (si hace falta corregir algo), `tests/test_resolution_schema.py` (nuevo).

**Criterios de aceptación:** los 5 sistemas actuales validan sin errores; tests de casos inválidos en verde; `pytest tests/` completo sigue en verde.

---

### Fase 11 — Auto-guardado de entidades + tags de mutación de estado
**Rama:** `feature/auto-guardado-vault` · **Complejidad:** medio · **Origen:** vtm-storyteller (#3) + Marinara-RPG-Extension (#8)

**Objetivo:** que el narrador pueda declarar, con una convención de etiquetas al final de su respuesta, nuevas entidades (`NAME:`/`CLAN:`/...) o mutaciones de estado (`[state: field=hp delta=-3 reason=...]`), y que el sistema las aplique automáticamente al vault/ficha sin que el usuario tenga que pedirlo explícitamente.

**Pasos:**
1. Definir la convención de etiquetas (nueva sección en `PromptBuilder` instruyendo al LLM cuándo y cómo emitirlas).
2. `narrator/agents/narrator_agent.py`: parser de ambos formatos (bloque de entidad nueva y tags de mutación inline), reutilizando `json_repair` de la Fase 3 donde aplique.
3. Conectar con `VaultWriter` (creación de nota de NPC/Locación) y con la ficha de personaje (`app_state["character"]`) para mutaciones de HP/condiciones/inventario.
4. Salvaguarda: nunca sobrescribir campos existentes sin marcar el cambio en el log de sesión (trazabilidad).
5. Tests con respuestas de ejemplo del LLM conteniendo ambas convenciones.

**Archivos:** `narrator/core/prompt_builder.py`, `narrator/agents/narrator_agent.py`, `narrator/core/vault_writer.py`, `tests/test_narrator_agent.py` (extender).

**Criterios de aceptación:** con una respuesta simulada del LLM que incluye ambas etiquetas, se crea el archivo de NPC esperado en el vault y se aplica la mutación de HP a la ficha; tests en verde.

---

### Fase 12 — Actores de NPC con contexto aislado
**Rama:** `feature/npc-contexto-aislado` · **Complejidad:** medio · **Origen:** loreweaver (#5)

**Objetivo:** cuando un NPC habla o decide, construir su prompt/contexto *solo* desde su propio registro (psique, agenda, conocimiento), nunca desde el pool completo del narrador — para prevenir que el LLM filtre secretos de Misterios/Frentes que ese NPC no debería conocer.

**Pasos:**
1. Revisar dónde hoy se genera diálogo/decisión de NPC con acceso a contexto amplio (`prompt_builder.build_npc_action_prompt`, `npc_routines.py`, partes de `world_agent.py`).
2. Refactorizar para que el prompt de NPC se arme exclusivamente desde su propio frontmatter (`npc_psyche`, agenda, facción) + el evento puntual que dispara la acción, sin inyectar `active_fronts`/`investigation_hint` del narrador general.
3. Test de regresión: un NPC con "conocimiento: ninguno sobre Misterio X" no debe recibir ese Misterio en su prompt aunque esté activo en el mundo.

**Archivos:** `narrator/core/prompt_builder.py` (`build_npc_action_prompt`), `narrator/agents/npc_routines.py`, `narrator/agents/world_agent.py`, `tests/test_npc_psyche.py` (extender).

**Criterios de aceptación:** test que arma un prompt de NPC y confirma ausencia de contenido de Misterios/Frentes no conocidos por ese NPC; `pytest tests/` en verde.

---

### Fase 13 — Detector estructural "dice-first"
**Rama:** `feature/dice-first-detector` · **Complejidad:** medio · **Origen:** loreweaver (#6)

**Objetivo:** formalizar en código (no solo en el prompt) la regla "el `RuleArbiter` resuelve, el LLM narra": detectar cuándo la acción del jugador requería tirada y cuándo la respuesta del narrador ya narra un resultado sin que se haya tirado, para poder corregir (una sola vez) en vez de dejar pasar la alucinación numérica.

**Pasos:**
1. `narrator/core/dice_first_guard.py` (nuevo): heurística sobre el texto del jugador (verbos de acción con incertidumbre) + heurística sobre la respuesta del narrador (lenguaje de resultado: "consigues", "fallás", "el golpe conecta").
2. Integrar en el flujo de `Orchestrator`/`app.py`: si se detecta narración de resultado sin tirada previa registrada en el turno, marcar el mensaje como sospechoso (log, no bloqueo automático — decisión de UX a validar).
3. Tests con pares (mensaje jugador, respuesta narrador) etiquetados manualmente como correcto/incorrecto.

**Archivos:** `narrator/core/dice_first_guard.py` (nuevo), `narrator/agents/orchestrator.py`, `tests/test_dice_first_guard.py` (nuevo).

**Criterios de aceptación:** tests con al menos 8 pares de ejemplo (4 correctos, 4 incorrectos) clasifican correctamente; no se bloquea el flujo de juego, solo se registra/advierte (a confirmar alcance exacto antes de implementar).

---

### Fase 14 — Entidad "Organizaciones/Facciones"
**Rama:** `feature/entidad-organizaciones` · **Complejidad:** medio · **Origen:** ttrpg-dm-toolkit (#9)

**Objetivo:** modelar facciones como entidad propia del vault (más allá de "Cofradías" actual), con goals/methods/resources/influencia y relaciones de alianza/enemistad con otras facciones.

**Pasos:**
1. Definir plantilla de frontmatter para `tipo: organizacion` (o extender `Cofradias/` si se decide reusar la carpeta) con los campos del informe.
2. Extender `extractor_agent.py` para poblar organizaciones detectadas en el manual (hoy solo genera NPCs/locaciones/facciones básicas).
3. Extender `retriever.py` con `get_by_type("organizacion")` y resumen para el prompt si es relevante en escena.
4. Tests de generación y lectura de una organización de ejemplo.

**Archivos:** `narrator/agents/extractor_agent.py`, `narrator/core/retriever.py`, `data/vault_template/Cofradias/` (o carpeta nueva si se decide), `tests/test_extractor_agent.py` (si existe, o nuevo).

**Criterios de aceptación:** al construir un vault de prueba, se genera al menos una organización con el esquema completo; búsqueda por tipo la recupera correctamente.

---

### Fase 15 — Entidad "Eventos" (timeline causa-efecto)
**Rama:** `feature/entidad-eventos` · **Complejidad:** medio · **Origen:** ttrpg-dm-toolkit (#10)

**Objetivo:** registrar hitos del mundo (históricos/actuales/programados) con causa/efecto/participantes, como historia persistente fuera de la memoria episódica de sesión.

**Pasos:**
1. Definir plantilla de frontmatter para `tipo: evento` (fecha/momento relativo, causa, efecto, participantes, tipo histórico/actual/programado).
2. Función en `vault_writer.py` para registrar un evento (llamada manual desde `app.py` o automática desde la Fase 11 de auto-guardado).
3. Extender `retriever.py` con acceso a eventos por rango/tipo.
4. Tests de creación y consulta de eventos.

**Archivos:** `narrator/core/vault_writer.py`, `narrator/core/retriever.py`, `data/vault_template/` (nueva carpeta `Eventos/`), `tests/test_vault_writer.py` (extender).

**Criterios de aceptación:** crear un evento de prueba genera el archivo esperado; consulta por tipo/rango lo recupera.

---

### Fase 16 — Deduplicación semántica de eventos de sesión
**Rama:** `feature/dedup-memoria` · **Complejidad:** medio · **Origen:** loreweaver (#18)

**Objetivo:** evitar que la memoria episódica (capa 2) registre el mismo hito narrativo dos veces con distinta redacción, dentro de una ventana de turnos cercanos.

**Pasos:**
1. En `memory_manager.py`, antes de agregar un resumen nuevo a la capa episódica, comparar contra los últimos N resúmenes (similitud por embeddings si están disponibles, o por overlap de keywords como fallback sin `nomic-embed-text`).
2. Definir umbral de similitud y ventana temporal (configurable).
3. Tests con pares de resúmenes parafraseados vs. genuinamente distintos.

**Archivos:** `narrator/core/memory_manager.py`, `tests/test_memory_manager.py` (extender).

**Criterios de aceptación:** tests confirman que un resumen parafraseado dentro de la ventana se descarta y uno genuinamente nuevo se conserva; `pytest tests/` en verde.

---

### Fase 17 — Extracción de fichas PDF vía campos AcroForm
**Rama:** `feature/pdf-acroform` · **Complejidad:** medio · **Origen:** vtm-storyteller (#19)

**Objetivo:** vía alternativa de extracción de ficha para PDFs rellenables oficiales (con campos de formulario), más robusta y rápida que la extracción de texto libre vía LLM cuando el PDF lo permite.

**Pasos:**
1. Agregar dependencia `PyPDF2` (o `pypdf`) — evaluar si ya cubre PyMuPDF, si no, justificar la dependencia nueva.
2. `sheet_parser.py`: detectar si el PDF tiene campos AcroForm; si los tiene, extraer vía `get_fields()` y mapear por convención de nombre; si no, caer al flujo actual (texto + LLM).
3. Mapeo de campos por sistema (empezar por VtM V20, que es el caso de referencia del repo analizado) en `data/systems/vtm_v20.yaml` o archivo de mapeo aparte.
4. Tests con un PDF de ficha rellenable de ejemplo (crear uno mínimo de prueba, sin datos reales de clientes/terceros).

**Archivos:** `narrator/core/sheet_parser.py`, `pyproject.toml` (dependencia nueva), `data/systems/vtm_v20.yaml` (mapeo de campos), `tests/test_sheet_parser.py` (extender).

**Criterios de aceptación:** con un PDF de prueba con campos AcroForm, la extracción puebla la ficha sin pasar por el LLM; con un PDF sin campos, el flujo cae correctamente al comportamiento actual sin romperse.

---

### Fase 18 — Búsqueda global cross-entidad en el vault
**Rama:** `feature/busqueda-global` · **Complejidad:** medio · **Origen:** ttrpg-dm-toolkit (#25)

**Objetivo:** buscar por texto libre sobre todo el vault (NPCs, locaciones, frentes, misterios, organizaciones, eventos) desde la GUI, con filtro por tipo, para navegación rápida durante la sesión.

**Pasos:**
1. `narrator/core/retriever.py`: función `search_all(query, tipo=None)` sobre el índice ya cargado (reusar keyword-match existente, sin necesidad de embeddings para esto).
2. UI mínima en `app.py`: campo de búsqueda + lista de resultados con tipo y link/apertura del archivo correspondiente.
3. Tests de búsqueda con distintos tipos de entidad presentes en un vault de prueba.

**Archivos:** `narrator/core/retriever.py`, `narrator/app.py`, `tests/test_retriever.py` (extender si existe, o nuevo).

**Criterios de aceptación:** búsqueda de un término presente en 2+ tipos de entidad devuelve ambos resultados correctamente etiquetados.

---

## BLOQUE 4 — Complejidad MEDIA-ALTA (fases 19 a 21)

### Fase 19 — Fog-of-war con feathering + trazos suavizados *(opcional, condicionada)*
**Rama:** `feature/fog-of-war-brush` · **Complejidad:** medio (mixto, algunas partes bajas) · **Origen:** Veilforge (#23)

**Objetivo:** solo si se decide agregar un modo de mapa visual táctico (hoy fuera del alcance narrativo-textual del proyecto) — pincel de revelado/ocultado de mapa con gradiente radial (feathering) y anotaciones a mano alzada suavizadas (Chaikin).

> ⚠️ **Nota de licencia:** Veilforge usa una licencia personal no comercial. Esta fase debe reimplementarse desde cero (algoritmos conocidos y públicos: gradiente radial, Chaikin), sin mirar/copiar su código fuente literal.

**Pasos:**
1. **Decisión previa requerida:** confirmar con Marcos si el modo mapa visual entra en el alcance del proyecto antes de tocar código (hoy el `ROADMAP.md` no lo contempla).
2. Si se aprueba: widget de canvas en Dear PyGui con `draw_layer`, máscara de revelado como matriz booleana o buffer de alpha.
3. Algoritmo de pincel circular con falloff radial (reimplementación propia).
4. Suavizado Chaikin para trazos de anotación (algoritmo público, trivial de reimplementar).
5. Tests del algoritmo de suavizado (entrada/salida de puntos) y de la máscara de revelado.

**Archivos:** `narrator/core/map_canvas.py` (nuevo, si se aprueba), `narrator/app.py`, `tests/test_map_canvas.py` (nuevo).

**Criterios de aceptación:** condicionado a aprobación de alcance; si se implementa, tests del algoritmo de suavizado y de la máscara en verde.

---

### Fase 20 — Harness IA-vs-IA con gate de calidad
**Rama:** `feature/harness-ia-vs-ia` · **Complejidad:** medio-alto · **Origen:** loreweaver (#1) — **es la Fase 4 del `ROADMAP.md` del proyecto**

**Objetivo:** construir el harness de testeo automatizado narrador-vs-jugador-IA: arquetipos de jugador simulados por un LLM (barato/local), jugando contra el narrador real, con métricas duras de calidad (fuga de secretos de Frentes/Misterios al jugador, tasa de "narró sin tirar" reutilizando el detector de la Fase 13) y un gate configurable (exit code) para poder correrlo como verificación repetible.

**Pasos:**
1. Definir 3-5 arquetipos de jugador (cauteloso, temerario, social, erudito, paranoico) como prompts de personalidad, reusando `llm_client.py`.
2. `narrator/agents/player_agent.py` (nuevo, es el ítem pendiente ya listado en el `ROADMAP.md` del proyecto: "IA jugadora que recibe escena y devuelve acción").
3. `scripts/playtest.py` (nuevo, fuera del paquete `narrator/`): loop headless narrador-real vs. jugador-simulado sobre el pipeline de turno real (`Orchestrator.build_narrator_context` + `LLMClient`), N turnos configurables.
4. Métrica de fuga: heurística de detección de contenido marcado como secreto (Misterios/Frentes) apareciendo literal o parafraseado en la narración cuando no debería.
5. Métrica dice-first-miss: reutiliza el detector de la Fase 13.
6. Reporte de salida (Markdown o JSON) con umbrales configurables y exit code no-cero si se superan.
7. Documentar cómo correrlo manualmente (no se automatiza en CI del estudio sin autorización aparte).

**Archivos:** `narrator/agents/player_agent.py` (nuevo), `scripts/playtest.py` (nuevo), `narrator/core/dice_first_guard.py` (reuso de Fase 13), `tests/test_player_agent.py` (nuevo, con mocks del LLM).

**Criterios de aceptación:** corrida de ejemplo de N turnos produce reporte con ambas métricas; con un caso sintético de fuga deliberada, el gate detecta y retorna exit code no-cero; tests con LLM mockeado en verde (no depende de Ollama corriendo para el test unitario).

**Nota:** esta es la fase más grande del roadmap — candidata a dividirse en sub-commits (arquetipos → player_agent → loop de playtest → métricas → gate) dentro de la misma rama, notificando cada commit según corresponde.

---

### Fase 21 — Import/export de NPCs como SillyTavern V2 character card *(opcional, nicho)*
**Rama:** `feature/sillytavern-card` · **Complejidad:** medio-alto · **Origen:** Marinara-RPG-Extension (#21)

**Objetivo:** permitir exportar/importar NPCs del vault en formato de tarjeta compatible con el ecosistema SillyTavern (PNG con chunk `tEXt` `chara`), para interoperabilidad con herramientas de terceros.

**Pasos:**
1. **Decisión previa recomendada:** confirmar si tiene valor real dado el uso mono-usuario del proyecto (es la fase más "nicho" del roadmap).
2. Si se aprueba: función de escritura de chunk PNG `tEXt` con el JSON de personaje en base64 (formato V2 card spec, es público).
3. Función de lectura/import inversa.
4. Tests de round-trip (exportar → importar → mismo contenido).

**Archivos:** `narrator/core/character_card.py` (nuevo, si se aprueba), `tests/test_character_card.py` (nuevo).

**Criterios de aceptación:** condicionado a aprobación; si se implementa, test de round-trip en verde.

---

## BLOQUE 5 — Complejidad ALTA (fase 22)

### Fase 22 — Narración por voz local (TTS) *(opcional, evaluar antes de comprometer esfuerzo)*
**Rama:** `feature/tts-local` · **Complejidad:** alto · **Origen:** idea de vtm-storyteller (#20) — implementación real 100% distinta (ellos usan cloud pago, acá tiene que ser local)

**Objetivo:** narración hablada opcional de la respuesta del narrador, con motor TTS 100% local (no cloud, coherente con el resto del proyecto).

**Pasos:**
1. **Spike previo obligatorio** (antes de comprometerse a la fase completa): evaluar candidatos locales (Piper, Coqui TTS, pyttsx3) en cuanto a calidad de voz en español, latencia y tamaño de instalación — reportar hallazgos antes de elegir.
2. Integración del motor elegido como proceso/hilo separado que no bloquee la GUI de Dear PyGui.
3. Toggle en `app.py` para activar/desactivar narración hablada.
4. Reproducción async del audio generado tras `finish_streaming`.
5. Manejo de cancelación (si el usuario envía un nuevo turno mientras se reproduce audio del anterior).

**Archivos:** `narrator/core/tts_engine.py` (nuevo), `narrator/app.py`, `pyproject.toml` (dependencia nueva — instalación de un motor TTS local puede chocar con el problema de SSL/certificados de la red de oficina; anticipar el workaround conocido antes de instalar).

**Criterios de aceptación:** spike documentado con recomendación concreta antes de implementar; una vez implementado, activar el toggle reproduce audio de una respuesta de prueba sin bloquear la UI ni el hilo de streaming del LLM.

**Nota:** es la única fase que requiere instalar una dependencia nueva de peso (modelo TTS) — coordinar con la Ley de Red-y-SSL antes de intentar la instalación.

---

## Tabla resumen (orden de ejecución)

| # | Fase | Rama | Complejidad |
|---|---|---|---|
| 1 | DSL reglas derivadas | `feature/dsl-reglas-derivadas` | Bajo |
| 2 | Tirada sugerida pendiente | `feature/tirada-sugerida` | Bajo |
| 3 | Robustez gen. NPCs (locking+JSON) | `feature/npc-gen-robustez` | Bajo |
| 4 | Factory multi-proveedor Ollama | `feature/llm-provider-factory` | Bajo |
| 5 | Lorebook por keywords | `feature/lorebook-keywords` | Bajo |
| 6 | Ideas Inbox | `feature/ideas-inbox` | Bajo |
| 7 | Cola de iniciativa | `feature/iniciativa-turnos` | Bajo |
| 8 | Metadata NPC + recall por mención | `feature/npc-metadata-recall` | Bajo-medio |
| 9 | `@tool` decorator | `feature/tool-decorator` | Bajo-medio |
| 10 | Taxonomía modos de resolución | `feature/taxonomia-resolucion` | Medio |
| 11 | Auto-guardado vault + tags de estado | `feature/auto-guardado-vault` | Medio |
| 12 | NPCs con contexto aislado | `feature/npc-contexto-aislado` | Medio |
| 13 | Detector dice-first | `feature/dice-first-detector` | Medio |
| 14 | Entidad Organizaciones | `feature/entidad-organizaciones` | Medio |
| 15 | Entidad Eventos | `feature/entidad-eventos` | Medio |
| 16 | Dedup semántica de memoria | `feature/dedup-memoria` | Medio |
| 17 | Extracción PDF AcroForm | `feature/pdf-acroform` | Medio |
| 18 | Búsqueda global en vault | `feature/busqueda-global` | Medio |
| 19 | Fog-of-war + trazos *(opcional)* | `feature/fog-of-war-brush` | Medio-alto |
| 20 | Harness IA-vs-IA | `feature/harness-ia-vs-ia` | Medio-alto |
| 21 | SillyTavern card *(opcional)* | `feature/sillytavern-card` | Medio-alto |
| 22 | TTS local *(opcional)* | `feature/tts-local` | Alto |

---

## Pendiente de aprobación

Este documento es la propuesta de roadmap. Por norma del estudio: **no se crea ninguna rama ni se toca código hasta aprobación explícita.** Al aprobar, se empieza por la **Fase 1** y se avanza en orden, verificando (tests + comportamiento) antes de pasar a la siguiente, con notificación previa a cada commit.
