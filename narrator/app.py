"""
AI NARRATOR — Motor de Rol con Ollama
======================================
GUI: Dear PyGui  |  Backend: narrator/core/ + narrator/agents/
"""

import dearpygui.dearpygui as dpg
from narrator.logger import logger
import fitz  # PyMuPDF
import requests
import threading
import queue as _queue_mod
import json
import random
import re
from pathlib import Path
from datetime import datetime

from narrator import PROJECT_ROOT
from narrator.core.llm_client import LLMClient
from narrator.core.session_manager import SessionManager
session_manager = SessionManager()


# ─────────────────────────────────────────────
#  GUI — HELPERS
# ─────────────────────────────────────────────
def add_spacer(h=8):
    dpg.add_spacer(height=h)

def section_label(text, parent=None):
    kwargs = {"label": text, "color": list(C_GOLD)}
    if parent:
        kwargs["parent"] = parent
    dpg.add_text(**kwargs)

def dim_text(text, parent=None):
    kwargs = {"label": text, "color": list(C_TEXT_DIM)}
    if parent:
        kwargs["parent"] = parent
    dpg.add_text(**kwargs)

# ─────────────────────────────────────────────
#  GUI — CHAT
# ─────────────────────────────────────────────
_streaming_token = ""
_is_streaming = False

def append_to_chat(role: str, text: str):
    if role == "user":
        label_color = list(C_GOLD)
        prefix = "[Vos]"
    elif role == "assistant":
        label_color = list(C_GOLD)
        prefix = "[Narrador]"
    else:
        label_color = list(C_TEXT_DIM)
        prefix = "[Sistema]"

    with dpg.group(parent="chat_scroll"):
        dpg.add_text(prefix, color=label_color)
        dpg.add_text(text, color=list(C_TEXT), wrap=_CHAT_WRAP_W)
        dpg.add_separator()
        dpg.add_spacer(height=4, parent="chat_scroll")

    dpg.set_y_scroll("chat_scroll", dpg.get_y_scroll_max("chat_scroll"))

def update_streaming_label(chunk: str):
    global _streaming_token
    _streaming_token += chunk
    display = _streaming_token[-600:] if len(_streaming_token) > 600 else _streaming_token
    _ui(lambda d=display: dpg.set_value("streaming_label", d))

def finish_streaming(full_text: str):
    global _is_streaming, _streaming_token
    _is_streaming = False
    _streaming_token = ""

    # Procesamiento sin DPG — hilo worker
    with state_lock:
        state["messages"].append({"role": "assistant", "content": full_text})

    is_important = False
    needs_char_refresh = False
    if _narrator_agent:
        is_important = _narrator_agent.is_important_event(full_text)
        char_data = _narrator_agent.extract_character_json(full_text)
        if char_data:
            with state_lock:
                state["character"].update(char_data)
            needs_char_refresh = True
    else:
        is_important = any(
            w in full_text.lower()
            for w in ["tirada", "dado", "d20", "éxito", "fallo", "consecuencia"]
        )

    if is_important:
        entry = f"[{datetime.now().strftime('%H:%M')}] {full_text[:120]}..."
        with state_lock:
            state["session_log"].append(entry)

    if _vault_writer and _AGENT_MODE:
        last_user = ""
        for m in reversed(state["messages"][:-1]):
            if m.get("role") == "user":
                last_user = m["content"]
                break
        session_n = state.get("session_number", 1)
        threading.Thread(
            target=_vault_writer.on_narrator_response,
            args=(last_user, full_text),
            kwargs={"session_number": session_n, "is_important": is_important},
            daemon=True,
        ).start()

    # Actualizaciones de DPG — encoladas para el hilo principal
    _refresh_char = needs_char_refresh
    _refresh_log = is_important

    def _ui_update():
        try:
            dpg.set_value("streaming_label", "")
            dpg.configure_item("streaming_group", show=False)
        except Exception as e:
            logger.error(f"Error inesperado: {e}", exc_info=True)
        append_to_chat("assistant", full_text)
        if _refresh_char:
            refresh_character_panel()
        if _refresh_log:
            refresh_log()
        dpg.enable_item("send_btn")
        dpg.enable_item("user_input")

    _ui(_ui_update)

def send_message(user_text: str = None):
    global _is_streaming, _streaming_token

    if _is_streaming:
        return

    if user_text is None:
        user_text = dpg.get_value("user_input").strip()

    if not user_text:
        return

    dpg.set_value("user_input", "")
    dpg.disable_item("send_btn")
    dpg.disable_item("user_input")

    if state["last_dice_result"]:
        user_text = f"{user_text}\n\n[RESULTADO DE DADOS: {state['last_dice_result']}]"
        state["last_dice_result"] = None

    state["messages"].append({"role": "user", "content": user_text})
    append_to_chat("user", user_text)

    if _AGENT_MODE and _orchestrator:
        event_type, intensity = _detect_event_type(user_text)
        state["ultimo_evento"] = event_type
        _orchestrator.record_event(event_type, intensity)

    if _AGENT_MODE and _orchestrator:
        try:
            system_content = _orchestrator.get_context_for_phase(state)
        except Exception as _e:
            print(f"⚠ Error en orquestador, usando modo legacy: {_e}")
            system_content = _build_legacy_context()
    else:
        system_content = _build_legacy_context()

    messages_to_send = [{"role": "system", "content": system_content}] + state["messages"]

    _is_streaming = True
    _streaming_token = ""
    try:
        dpg.configure_item("streaming_group", show=True)
        dpg.set_value("streaming_label", "...")
    except Exception as e:
        logger.error(f"Error inesperado: {e}", exc_info=True)

    def run():
        LLMClient(model=state["model"]).stream_chat(messages_to_send, update_streaming_label, finish_streaming)

    threading.Thread(target=run, daemon=True).start()

# ─────────────────────────────────────────────
#  GUI — DICE PANEL
# ─────────────────────────────────────────────
def do_roll(sides: int):
    try:
        n = int(dpg.get_value(f"dice_count_{sides}"))
    except Exception as e:
        n = 1
    n = max(1, min(n, 20))

    rolls = roll_dice(n, sides)
    total = sum(rolls)
    result_str = format_roll_result(rolls, sides)

    state["last_dice_result"] = f"{n}D{sides}: {result_str}"

    color = list(C_RED_BRIGHT) if total == sides * n else (
        list(C_GOLD) if total >= sides * n * 0.75 else list(C_TEXT)
    )
    dpg.set_value("dice_result_main", f"{n}D{sides}")
    dpg.set_value("dice_result_total", str(total))
    dpg.configure_item("dice_result_total", color=color)
    dpg.set_value("dice_result_detail", result_str)

    entry = f"[{datetime.now().strftime('%H:%M')}] {n}D{sides} → {result_str}"
    state["session_log"].append(entry)
    refresh_log()

    if _vault_writer:
        _vault_writer.log_dice_roll(f"{n}D{sides} → {result_str}")

def build_dice_panel(parent):
    section_label("DADOS", parent=parent)
    dpg.add_spacer(height=6, parent=parent)

    for sides in DICE_TYPES:
        with dpg.group(horizontal=True, parent=parent):
            dpg.add_input_int(
                tag=f"dice_count_{sides}",
                default_value=1,
                min_value=1,
                max_value=20,
                width=55,
                min_clamped=True,
                max_clamped=True,
            )
            dpg.add_button(
                label=f"D{sides}",
                width=72,
                height=32,
                callback=lambda s, a, u=sides: do_roll(u),
            )
        dpg.add_spacer(height=4, parent=parent)

    dpg.add_spacer(height=10, parent=parent)
    dpg.add_separator(parent=parent)
    dpg.add_spacer(height=8, parent=parent)

    dpg.add_text("Última tirada:", color=list(C_TEXT_DIM), parent=parent)
    dpg.add_text("—", tag="dice_result_main", color=list(C_GOLD_DIM), parent=parent)
    dpg.add_text("—", tag="dice_result_total", color=list(C_TEXT), parent=parent)
    dpg.add_text("", tag="dice_result_detail", color=list(C_TEXT_DIM), wrap=160, parent=parent)

    dpg.add_spacer(height=10, parent=parent)
    dpg.add_button(
        label="Enviar resultado",
        parent=parent,
        width=170,
        callback=lambda: send_message(
            "El resultado de mi tirada fue: " + (state["last_dice_result"] or "ninguna")
        )
    )

# ─────────────────────────────────────────────
#  GUI — CHARACTER SHEET (schema-driven)
# ─────────────────────────────────────────────
def _dots(value, max_val: int = 5) -> str:
    try:
        v = max(0, min(int(value), max_val))
    except (ValueError, TypeError):
        v = 0
    return "●" * v + "○" * (max_val - v)

def _stat(value) -> str:
    try:
        v = int(value)
        mod = (v - 10) // 2
        return f"{v} ({'+' if mod >= 0 else ''}{mod})"
    except (ValueError, TypeError):
        return str(value)

def _render_field(label: str, value, display: str, ftype: str, max_val: int, parent: str):
    with dpg.group(horizontal=True, parent=parent):
        dpg.add_text(f"{label}:", color=list(C_TEXT_DIM), wrap=72)
        if value is None or value == "":
            dpg.add_text("—", color=list(C_TEXT_DARK))
        elif isinstance(value, list):
            dpg.add_text(", ".join(str(x) for x in value), color=list(C_TEXT), wrap=88)
        elif display == "dots" and ftype == "int":
            dpg.add_text(_dots(value, max_val), color=list(C_GOLD))
        elif display == "stat_block" and ftype == "int":
            dpg.add_text(_stat(value), color=list(C_TEXT))
        else:
            dpg.add_text(str(value), color=list(C_TEXT), wrap=88)

def _render_section(section: dict, char: dict, parent: str, rendered: set):
    display = section.get("display", "default")
    dpg.add_text(section.get("name", "").upper(), color=list(C_GOLD_DIM), parent=parent)
    for field in section.get("fields", []):
        key = field.get("key", "")
        rendered.add(key)
        value = char.get(key)
        if value is None:
            continue
        _render_field(
            label=field.get("label", key),
            value=value,
            display=display,
            ftype=field.get("type", "string"),
            max_val=field.get("max", 5),
            parent=parent,
        )
    dpg.add_spacer(height=5, parent=parent)

def refresh_character_panel():
    try:
        dpg.delete_item("char_content", children_only=True)
    except Exception as e:
        return

    char = state["character"]
    if not char:
        dpg.add_text("Sin personaje creado.", parent="char_content", color=list(C_TEXT_DIM))
        dpg.add_spacer(height=6, parent="char_content")
        dpg.add_text("Cargá un manual y pedile\nal narrador que te guíe.",
                     parent="char_content", color=list(C_TEXT_DIM), wrap=160)
        return

    # Intentar cargar schema del sistema activo
    schema = None
    if _AGENT_MODE and _orchestrator:
        try:
            sys_data = _orchestrator.builder.load_system(state.get("system_slug", "generic"))
            schema = sys_data.get("character_sheet_schema")
        except Exception as e:
            logger.error(f"Error inesperado: {e}", exc_info=True)

    if not schema:
        # Fallback genérico si no hay schema
        for key, val in char.items():
            with dpg.group(horizontal=False, parent="char_content"):
                dpg.add_text(str(key).replace("_", " ").upper(), color=list(C_GOLD_DIM))
                if isinstance(val, dict):
                    for k2, v2 in val.items():
                        dpg.add_text(f"  {k2}: {v2}", color=list(C_TEXT), wrap=160)
                elif isinstance(val, list):
                    dpg.add_text(", ".join(str(x) for x in val), color=list(C_TEXT), wrap=160)
                else:
                    dpg.add_text(str(val), color=list(C_TEXT), wrap=160)
                add_spacer(4)
        return

    rendered: set = set()
    archetype_key = schema.get("archetype_key", "")
    archetype_val = str(char.get(archetype_key, "")).lower().strip() if archetype_key else ""

    # Secciones base
    for section in schema.get("base_sections", []):
        _render_section(section, char, "char_content", rendered)

    # Secciones condicionales según clan/clase/tipo
    if archetype_val:
        cond = schema.get("conditional_sections", {})
        for cond_key, sections in cond.items():
            if cond_key.lower() == archetype_val:
                for section in sections:
                    _render_section(section, char, "char_content", rendered)
                break

    # Extras: campos que el LLM generó fuera del schema
    extras = {k: v for k, v in char.items() if k not in rendered}
    if extras:
        dpg.add_text("OTROS", color=list(C_GOLD_DIM), parent="char_content")
        for key, val in extras.items():
            _render_field(
                label=key.replace("_", " ").title(),
                value=val,
                display="default",
                ftype="string",
                max_val=5,
                parent="char_content",
            )
        dpg.add_spacer(height=4, parent="char_content")

# ─────────────────────────────────────────────
#  GUI — SESSION LOG
# ─────────────────────────────────────────────
def refresh_log():
    try:
        dpg.delete_item("log_content", children_only=True)
        for entry in state["session_log"][-20:]:
            dpg.add_text(entry, parent="log_content", color=list(C_TEXT_DIM), wrap=160)
            dpg.add_spacer(height=2, parent="log_content")
    except Exception as e:
        logger.error(f"Error inesperado: {e}", exc_info=True)

# ─────────────────────────────────────────────
#  GUI — ESTADO (relojes de frentes) — Sprint 3
# ─────────────────────────────────────────────
def _clock_bar(tick: int, max_ticks: int) -> str:
    """Genera una barra ASCII de progreso para el reloj de un frente."""
    filled = min(tick, max_ticks)
    bar = "█" * filled + "░" * (max_ticks - filled)
    return f"[{bar}] {filled}/{max_ticks}"

def refresh_estado_panel():
    try:
        dpg.delete_item("estado_content", children_only=True)
    except Exception as e:
        return

    # Número de sesión
    dpg.add_text(
        f"Sesión #{state.get('session_number', 1)}",
        parent="estado_content",
        color=list(C_GOLD),
    )
    dpg.add_separator(parent="estado_content")
    dpg.add_spacer(height=4, parent="estado_content")

    # Sistema
    sys_name = state.get("system_name", "") or "—"
    dpg.add_text(f"Sistema:", parent="estado_content", color=list(C_TEXT_DIM))
    dpg.add_text(sys_name, parent="estado_content", color=list(C_TEXT), wrap=155)
    dpg.add_spacer(height=6, parent="estado_content")

    # Relojes de frentes
    if _AGENT_MODE and _orchestrator:
        try:
            fronts = _orchestrator.retriever.get_fronts_with_clocks()
        except Exception as e:
            fronts = []
    else:
        fronts = []

    if fronts:
        dpg.add_text("FRENTES:", parent="estado_content", color=list(C_GOLD_DIM))
        dpg.add_spacer(height=4, parent="estado_content")
        for f in fronts:
            dpg.add_text(f["nombre"], parent="estado_content", color=list(C_TEXT), wrap=155)
            bar = _clock_bar(f["tick"], f["max"])
            estado_color = list(C_RED_BRIGHT) if f["estado"] != "latente" else list(C_TEXT_DIM)
            dpg.add_text(bar, parent="estado_content", color=estado_color)
            if f.get("escasez"):
                dpg.add_text(f"  {f['escasez']}", parent="estado_content",
                             color=list(C_TEXT_DIM), wrap=155)
            dpg.add_spacer(height=4, parent="estado_content")
    else:
        dpg.add_text("Sin frentes activos.", parent="estado_content", color=list(C_TEXT_DIM))
        dpg.add_text("Construí el vault primero.", parent="estado_content",
                     color=list(C_TEXT_DIM), wrap=155)

# ─────────────────────────────────────────────
#  MULTI-PDF — carga suplementos adicionales
# ─────────────────────────────────────────────
def add_supplement_callback(sender, app_data):
    """Carga un PDF adicional y acumula su texto en manual_text."""
    if not app_data or "file_path_name" not in app_data:
        return
    path = app_data["file_path_name"]
    name = Path(path).name

    def process():
        text = extract_pdf_text(path, max_chars=8000)
        separator = f"\n\n{'='*60}\n=== SUPLEMENTO: {name} ===\n{'='*60}\n\n"
        with state_lock:
            state["manual_text"] += separator + text
            state["manual_names"].append(name)
            names_str = ", ".join(state["manual_names"])
        _ui(lambda ns=names_str, n=name: (
            dpg.set_value("manual_status", f"✓ {ns}"),
            append_to_chat("system", f"Suplemento añadido: {n}"),
        ))

    threading.Thread(target=process, daemon=True).start()


# ─────────────────────────────────────────────
#  EXPORTAR LOG DE SESIÓN
# ─────────────────────────────────────────────
def export_session_log(silent: bool = False) -> str:
    """Exporta el historial de chat completo como Markdown. Devuelve la ruta."""
    session_n = state.get("session_number", 1)
    date_str = datetime.now().strftime("%Y-%m-%d_%H-%M")
    filename = f"Sesion_{session_n:02d}_export_{date_str}.md"
    export_path = session_manager.save_dir / filename

    lines = [
        f"# Sesión {session_n} — {datetime.now().strftime('%Y-%m-%d')}",
        f"**Sistema:** {state.get('system_name', '—')}",
        f"**Manual:** {state.get('manual_name', '—')}",
        "",
        "---",
        "",
        "## Transcripción",
        "",
    ]

    for msg in state["messages"]:
        role = msg.get("role", "")
        content = msg.get("content", "")
        if role == "user":
            lines.append(f"**Jugador:** {content}")
        elif role == "assistant":
            lines.append(f"**Narrador:** {content}")
        lines.append("")

    if state["session_log"]:
        lines += ["---", "", "## Log de Eventos", ""]
        lines += [f"- {e}" for e in state["session_log"]]

    if state.get("character"):
        lines += [
            "", "---", "", "## Hoja de Personaje (snapshot)", "",
            "```json",
            json.dumps(state["character"], ensure_ascii=False, indent=2),
            "```",
        ]

    if _AGENT_MODE and _orchestrator:
        clocks = _orchestrator.state.get_clocks_summary()
        if clocks:
            lines += ["", "---", "", "## Estado de Frentes", "", "```", clocks, "```"]

    export_path.write_text("\n".join(lines), encoding="utf-8")

    if _AGENT_MODE and _orchestrator:
        config = _orchestrator.config
        vault_path = Path(config.get("vault", {}).get("path", "vault"))
        sessions_dir = vault_path / "Sesiones"
        if sessions_dir.exists():
            import shutil
            shutil.copy(export_path, sessions_dir / filename)

    if not silent:
        append_to_chat("system", f"Log exportado: {export_path}")
    return str(export_path)


# ─────────────────────────────────────────────
#  EDITOR DE HOJA DE PERSONAJE
# ─────────────────────────────────────────────
def refresh_character_editor():
    """Actualiza el editor JSON con los datos actuales del personaje."""
    try:
        json_str = json.dumps(state["character"], ensure_ascii=False, indent=2)
        dpg.set_value("char_json_editor", json_str)
    except Exception as e:
        logger.error(f"Error inesperado: {e}", exc_info=True)

def apply_character_edits():
    """Lee el JSON del editor, valida y aplica al estado."""
    try:
        raw = dpg.get_value("char_json_editor")
        data = json.loads(raw)
        if isinstance(data, dict):
            state["character"] = data
            refresh_character_panel()
            refresh_character_editor()
            append_to_chat("system", "Hoja de personaje actualizada.")
        else:
            append_to_chat("system", "⚠ El JSON debe ser un objeto {}.")
    except json.JSONDecodeError as e:
        append_to_chat("system", f"⚠ JSON inválido: {e}")


# ─────────────────────────────────────────────
#  WORLD AGENT — avance autónomo del mundo
# ─────────────────────────────────────────────
def run_world_agent():
    """Lanza el WorldAgent en un hilo secundario."""
    if not _AGENT_MODE or not _orchestrator:
        append_to_chat("system", "⚠ Modo agentes no disponible.")
        return

    try:
        dpg.disable_item("world_advance_btn")
    except Exception as e:
        logger.error(f"Error inesperado: {e}", exc_info=True)
    _ui(lambda: _proc_start("Avanzando el mundo entre sesiones..."))

    def on_progress(msg: str):
        _ui(lambda m=msg: _proc_step(m))

    def run():
        try:
            llm = LLMClient(model=state["model"])
            agent = WorldAgent(
                llm=llm,
                retriever=_orchestrator.retriever,
                state=_orchestrator.state,
            )
            result = agent.run(
                system_slug=state.get("system_slug", "generic"),
                session_number=state.get("session_number", 1),
                on_progress=on_progress,
            )
            for adv in result.get("advances", []):
                _orchestrator.state.advance_front_clock(adv.get("nombre", ""), adv.get("ticks", 1))
                _orchestrator.world_sim.advance_front(adv.get("nombre", ""), adv.get("ticks", 1))
            summary = (
                f"Mundo avanzado: {result['frentes_avanzados']} frentes, "
                f"{result['npcs_simulados']} NPCs simulados.\n\n"
                f"{result['narrativa']}"
            )
            _ui(lambda s=summary: (_proc_done(s), refresh_estado_panel()))
        except Exception as e:
            _ui(lambda err=str(e): _proc_done(f"Error en World Agent: {err}"))
        finally:
            _ui(lambda: dpg.enable_item("world_advance_btn"))

    threading.Thread(target=run, daemon=True).start()


# ─────────────────────────────────────────────
#  GUI — PDF LOADER
# ─────────────────────────────────────────────
def load_pdf_callback(sender, app_data):
    if not app_data or "file_path_name" not in app_data:
        return

    path = app_data["file_path_name"]
    name = Path(path).name

    dpg.set_value("manual_status", f"Cargando {name}...")

    def process():
        text = extract_pdf_text(path)
        system_name, system_slug = detect_system(text)
        with state_lock:
            state["manual_text"] = text
            state["manual_name"] = name
            state["manual_names"] = [name]
            state["system_name"] = system_name
            state["system_slug"] = system_slug
            state["phase"] = "char_creation"

        analysis_prompt = (
            f"Acabo de cargar el manual '{name}'. "
            f"Sistema detectado: {system_name}. "
            f"Presentame las opciones principales para crear un personaje "
            f"(clanes, razas, clases, arquetipos según el sistema) "
            f"con un menú numerado y sabor narrativo. "
            f"Cuando elija, guiame por las secciones de la hoja. "
            f"Incluí datos del personaje en bloques ```json``` para actualizar la hoja."
        )

        def _update(sn=system_name, n=name, ap=analysis_prompt):
            dpg.set_value("manual_status", f"✓ {n}")
            dpg.set_value("system_detected", sn)
            try:
                dpg.enable_item("build_vault_btn")
                dpg.enable_item("add_pdf_btn")
            except Exception as e:
                logger.error(f"Error inesperado: {e}", exc_info=True)
            append_to_chat("system", f"Manual cargado: {n}\nSistema: {sn}")
            send_message(ap)

        _ui(_update)

    threading.Thread(target=process, daemon=True).start()

# ─────────────────────────────────────────────
#  GUI — VAULT BUILDER
# ─────────────────────────────────────────────
def build_vault_callback():
    if not state.get("manual_text"):
        append_to_chat("system", "⚠ Primero cargá un manual PDF.")
        return
    if not _AGENT_MODE:
        append_to_chat("system", "⚠ Modo agentes no disponible.")
        return

    try:
        dpg.disable_item("build_vault_btn")
    except Exception as e:
        logger.error(f"Error inesperado: {e}", exc_info=True)
    _ui(lambda: _proc_start("Construyendo vault del sistema..."))

    def on_progress(msg: str):
        _ui(lambda m=msg: _proc_step(m))

    def run():
        try:
            llm = LLMClient(model=state["model"])
            pb = PromptBuilder()
            extractor = ExtractorAgent(llm=llm, builder=pb)

            config = _orchestrator.config if _orchestrator else {}
            vault_path = config.get("vault", {}).get("path", "vault")
            template_path = config.get("vault", {}).get("template_path", "data/vault_template")

            result = extractor.run(
                pdf_text=state["manual_text"],
                system_slug=state["system_slug"],
                system_name=state["system_name"],
                vault_path=vault_path,
                template_path=template_path,
                on_progress=on_progress,
            )
            summary = (
                f"Vault construido: {result['npcs']} NPCs, "
                f"{result['locaciones']} locaciones, "
                f"{result['facciones']} facciones, "
                f"{result['frentes']} frentes.\n"
                f"Abri vault/ en Obsidian para explorar."
            )
            _ui(lambda s=summary: (_proc_done(s), refresh_estado_panel()))
        except Exception as e:
            _ui(lambda err=str(e): _proc_done(f"Error construyendo vault: {err}"))
        finally:
            _ui(lambda: dpg.enable_item("build_vault_btn"))

    threading.Thread(target=run, daemon=True).start()

# ─────────────────────────────────────────────
#  GUI — QUICK ACTIONS
# ─────────────────────────────────────────────
QUICK_ACTIONS = [
    ("Atacar", "Quiero atacar al enemigo más cercano."),
    ("Investigar", "Examino el entorno en busca de pistas o peligros ocultos."),
    ("Negociar", "Intento hablar y negociar con el PNJ."),
    ("Huir", "Intento escapar de la situación actual."),
    ("Descansar", "El grupo se detiene a descansar y recuperarse."),
    ("Situacion", "¿Qué está pasando exactamente? Describí la escena."),
]

# ─────────────────────────────────────────────
#  GUI — THEME
# ─────────────────────────────────────────────
def apply_theme():
    with dpg.theme() as global_theme:
        with dpg.theme_component(dpg.mvAll):
            dpg.add_theme_color(dpg.mvThemeCol_WindowBg, C_BG)
            dpg.add_theme_color(dpg.mvThemeCol_ChildBg, C_PANEL)
            dpg.add_theme_color(dpg.mvThemeCol_PopupBg, C_SURFACE)
            dpg.add_theme_color(dpg.mvThemeCol_Border, C_BORDER)
            dpg.add_theme_color(dpg.mvThemeCol_FrameBg, C_INPUT_BG)
            dpg.add_theme_color(dpg.mvThemeCol_FrameBgHovered, C_HOVER)
            dpg.add_theme_color(dpg.mvThemeCol_FrameBgActive, C_ACTIVE)
            dpg.add_theme_color(dpg.mvThemeCol_Button, C_SURFACE)
            dpg.add_theme_color(dpg.mvThemeCol_ButtonHovered, C_HOVER)
            dpg.add_theme_color(dpg.mvThemeCol_ButtonActive, C_ACTIVE)
            dpg.add_theme_color(dpg.mvThemeCol_Header, C_SURFACE)
            dpg.add_theme_color(dpg.mvThemeCol_HeaderHovered, C_HOVER)
            dpg.add_theme_color(dpg.mvThemeCol_HeaderActive, C_ACTIVE)
            dpg.add_theme_color(dpg.mvThemeCol_TitleBg, C_PANEL)
            dpg.add_theme_color(dpg.mvThemeCol_TitleBgActive, C_SURFACE)
            dpg.add_theme_color(dpg.mvThemeCol_MenuBarBg, C_PANEL)
            dpg.add_theme_color(dpg.mvThemeCol_ScrollbarBg, C_BG)
            dpg.add_theme_color(dpg.mvThemeCol_ScrollbarGrab, C_BORDER)
            dpg.add_theme_color(dpg.mvThemeCol_ScrollbarGrabHovered, C_GOLD_DIM)
            dpg.add_theme_color(dpg.mvThemeCol_ScrollbarGrabActive, C_GOLD)
            dpg.add_theme_color(dpg.mvThemeCol_CheckMark, C_GOLD)
            dpg.add_theme_color(dpg.mvThemeCol_SliderGrab, C_GOLD)
            dpg.add_theme_color(dpg.mvThemeCol_SliderGrabActive, C_GOLD)
            dpg.add_theme_color(dpg.mvThemeCol_Text, C_TEXT)
            dpg.add_theme_color(dpg.mvThemeCol_Separator, C_BORDER)
            dpg.add_theme_color(dpg.mvThemeCol_SeparatorHovered, C_GOLD_DIM)
            dpg.add_theme_color(dpg.mvThemeCol_Tab, C_PANEL)
            dpg.add_theme_color(dpg.mvThemeCol_TabHovered, C_HOVER)
            dpg.add_theme_color(dpg.mvThemeCol_TabActive, C_SURFACE)

            dpg.add_theme_style(dpg.mvStyleVar_WindowRounding, 4)
            dpg.add_theme_style(dpg.mvStyleVar_FrameRounding, 3)
            dpg.add_theme_style(dpg.mvStyleVar_GrabRounding, 3)
            dpg.add_theme_style(dpg.mvStyleVar_TabRounding, 3)
            dpg.add_theme_style(dpg.mvStyleVar_ChildRounding, 4)
            dpg.add_theme_style(dpg.mvStyleVar_PopupRounding, 4)
            dpg.add_theme_style(dpg.mvStyleVar_FramePadding, 8, 5)
            dpg.add_theme_style(dpg.mvStyleVar_ItemSpacing, 8, 6)
            dpg.add_theme_style(dpg.mvStyleVar_WindowPadding, 12, 10)
            dpg.add_theme_style(dpg.mvStyleVar_ScrollbarSize, 10)

    dpg.bind_theme(global_theme)

    with dpg.theme() as dice_theme:
        with dpg.theme_component(dpg.mvButton):
            dpg.add_theme_color(dpg.mvThemeCol_Button, C_RED)
            dpg.add_theme_color(dpg.mvThemeCol_ButtonHovered, C_RED_BRIGHT)
            dpg.add_theme_color(dpg.mvThemeCol_ButtonActive, (210, 70, 78, 255))
            dpg.add_theme_color(dpg.mvThemeCol_Text, (230, 230, 240, 255))
    state["dice_theme"] = dice_theme

    with dpg.theme() as send_theme:
        with dpg.theme_component(dpg.mvButton):
            dpg.add_theme_color(dpg.mvThemeCol_Button, C_GOLD_DIM)
            dpg.add_theme_color(dpg.mvThemeCol_ButtonHovered, C_GOLD)
            dpg.add_theme_color(dpg.mvThemeCol_ButtonActive, (120, 175, 230, 255))
            dpg.add_theme_color(dpg.mvThemeCol_Text, C_BG)
    state["send_theme"] = send_theme

    with dpg.theme() as action_theme:
        with dpg.theme_component(dpg.mvButton):
            dpg.add_theme_color(dpg.mvThemeCol_Button, (18, 26, 40, 255))
            dpg.add_theme_color(dpg.mvThemeCol_ButtonHovered, C_HOVER)
            dpg.add_theme_color(dpg.mvThemeCol_ButtonActive, C_ACTIVE)
            dpg.add_theme_color(dpg.mvThemeCol_Text, C_GOLD)
            dpg.add_theme_style(dpg.mvStyleVar_FrameRounding, 2)
    state["action_theme"] = action_theme

# ─────────────────────────────────────────────
#  GUI — MAIN WINDOW
# ─────────────────────────────────────────────
def build_gui():
    global _CHAT_WRAP_W
    dpg.create_context()
    dpg.create_viewport(title=APP_TITLE, min_width=900, min_height=600, resizable=True)
    apply_theme()
    dpg.setup_dearpygui()
    dpg.show_viewport()
    dpg.maximize_viewport()
    dpg.render_dearpygui_frame()   # deja que el maximize tome efecto

    W = dpg.get_viewport_client_width()
    H = dpg.get_viewport_client_height()

    COL_L   = 195
    COL_R   = 190
    CHAT_W  = W - COL_L - COL_R - 20
    _CHAT_WRAP_W = CHAT_W - 32
    PANEL_H = H - 68

    # ── File dialogs ──────────────────────────────────────────
    dpg.add_file_dialog(
        tag="pdf_dialog", directory_selector=False, show=False,
        callback=load_pdf_callback, width=700, height=450, modal=True,
    )
    dpg.add_file_extension(".pdf", parent="pdf_dialog", color=list(C_GOLD))
    dpg.add_file_extension(".PDF", parent="pdf_dialog", color=list(C_GOLD))

    dpg.add_file_dialog(
        tag="pdf_supplement_dialog", directory_selector=False, show=False,
        callback=add_supplement_callback, width=700, height=450, modal=True,
    )
    dpg.add_file_extension(".pdf", parent="pdf_supplement_dialog", color=list(C_GOLD_DIM))
    dpg.add_file_extension(".PDF", parent="pdf_supplement_dialog", color=list(C_GOLD_DIM))

    # ── Ventana de progreso flotante ──────────────────────────
    with dpg.window(tag="proc_detail_window",
                    label="Proceso en segundo plano",
                    show=False, width=480, height=370, no_close=False,
                    pos=[W // 2 - 240, H // 2 - 185]):
        dpg.add_text("", tag="proc_detail_header", color=list(C_GOLD))
        dpg.add_separator()
        dpg.add_spacer(height=4)
        dpg.add_text(
            "Este proceso corre en segundo plano.\n"
            "Podes seguir jugando mientras tanto.",
            color=list(C_TEXT_DIM), wrap=440,
        )
        dpg.add_spacer(height=6)
        with dpg.child_window(tag="proc_log_area", height=220, border=True,
                              horizontal_scrollbar=False):
            dpg.add_text("En espera...", color=list(C_TEXT_DARK))
        dpg.add_spacer(height=6)
        dpg.add_button(label="Ocultar", width=-1,
                       callback=lambda: dpg.configure_item("proc_detail_window", show=False))

    # ── Ventana principal ─────────────────────────────────────
    with dpg.window(tag="main_window", no_title_bar=True, no_move=True,
                    no_resize=True, no_scrollbar=True):

        # ── HEADER ───────────────────────────────────────────
        with dpg.group(horizontal=True):
            dpg.add_text("AI NARRATOR", color=list(C_GOLD))
            dpg.add_spacer(width=10)
            dpg.add_text("Modelo:", color=list(C_TEXT_DIM))
            models = LLMClient().get_models()
            state["models"] = models
            if not models:
                models = ["(sin Ollama)"]
            dpg.add_combo(tag="model_selector", items=models,
                          default_value=models[0], width=170,
                          callback=lambda s, a: state.update({"model": a}))
            dpg.add_spacer(width=8)
            dpg.add_text("Manual:", color=list(C_TEXT_DIM))
            dpg.add_text("(ninguno)", tag="manual_status", color=list(C_TEXT_DIM))
            dpg.add_button(label="Cargar PDF",
                           callback=lambda: dpg.show_item("pdf_dialog"))
            dpg.add_button(tag="add_pdf_btn", label="+ Supl.",
                           callback=lambda: dpg.show_item("pdf_supplement_dialog"),
                           enabled=False)
            dpg.add_spacer(width=8)
            dpg.add_text("Sistema:", color=list(C_TEXT_DIM))
            dpg.add_text("--", tag="system_detected", color=list(C_TEXT_DIM))
            dpg.add_spacer(width=8)
            dpg.add_button(tag="build_vault_btn", label="Vault",
                           callback=build_vault_callback, enabled=False)
            dpg.add_button(label="Guardar",
                           callback=lambda: (session_manager.save_session(state),
                                             append_to_chat("system", "Sesion guardada.")))

        dpg.add_separator()
        dpg.add_spacer(height=2)

        # ── LAYOUT 3 COLUMNAS ────────────────────────────────
        with dpg.group(horizontal=True):

            # ══ IZQUIERDA: personaje + dados ══
            with dpg.child_window(width=COL_L, height=PANEL_H, border=True,
                                  tag="left_panel"):
                dpg.add_spacer(height=4)
                with dpg.tab_bar():

                    with dpg.tab(label="Personaje"):
                        dpg.add_spacer(height=4)
                        with dpg.child_window(tag="char_content",
                                              height=PANEL_H - 230,
                                              border=False):
                            dim_text("Sin personaje.")
                        dpg.add_spacer(height=4)
                        dpg.add_button(label="Actualizar hoja", width=-1,
                                       callback=refresh_character_panel)
                        dpg.add_separator()
                        dpg.add_spacer(height=3)
                        dim_text("Editar (JSON):")
                        dpg.add_input_text(
                            tag="char_json_editor", multiline=True,
                            width=-1, height=100,
                            hint='{"nombre": "...", ...}',
                        )
                        dpg.add_spacer(height=3)
                        dpg.add_button(label="Aplicar cambios", width=-1,
                                       callback=apply_character_edits)

                    with dpg.tab(label="Dados"):
                        dpg.add_spacer(height=4)
                        build_dice_panel(dpg.last_item())

            dpg.add_spacer(width=4)

            # ══ CENTRO: chat ══
            with dpg.child_window(width=CHAT_W, height=PANEL_H, border=True):

                # Quick actions — una sola fila
                btn_w = max(80, (CHAT_W - 12) // len(QUICK_ACTIONS))
                with dpg.group(horizontal=True):
                    for lbl, msg in QUICK_ACTIONS:
                        btn = dpg.add_button(
                            label=lbl, width=btn_w,
                            callback=lambda s, a, m=msg: send_message(m),
                        )
                        dpg.bind_item_theme(btn, state["action_theme"])
                dpg.add_separator()

                # Barra de progreso (oculta hasta que haya proceso activo)
                with dpg.group(tag="proc_bar_group", show=False):
                    dpg.add_spacer(height=2)
                    with dpg.group(horizontal=True):
                        dpg.add_text("[...]", color=list(C_GOLD))
                        dpg.add_spacer(width=4)
                        dpg.add_text("", tag="proc_bar_text", color=list(C_TEXT_DIM))
                        dpg.add_spacer(width=6)
                        dpg.add_button(
                            label="Detalles",
                            callback=lambda: dpg.configure_item(
                                "proc_detail_window", show=True),
                        )
                        dpg.add_button(
                            label=" x ",
                            callback=lambda: dpg.configure_item(
                                "proc_bar_group", show=False),
                        )
                    dpg.add_spacer(height=2)
                    dpg.add_separator()

                # Scroll de chat
                CHAT_H = PANEL_H - 100
                with dpg.child_window(tag="chat_scroll", height=CHAT_H,
                                      border=False, horizontal_scrollbar=False):
                    dpg.add_text(
                        "Bienvenido al AI Narrator.\n"
                        "Carga un manual PDF para comenzar la creacion de personaje,\n"
                        "o escribi directamente para iniciar una aventura.",
                        color=list(C_TEXT_DIM), wrap=_CHAT_WRAP_W,
                    )
                    dpg.add_separator()
                    with dpg.group(tag="streaming_group", show=False):
                        dpg.add_text("[Narrador]", color=list(C_GOLD))
                        dpg.add_text("", tag="streaming_label",
                                     color=list(C_TEXT), wrap=_CHAT_WRAP_W)
                        dpg.add_separator()

                dpg.add_spacer(height=3)

                # Input
                with dpg.group(horizontal=True):
                    dpg.add_input_text(
                        tag="user_input",
                        hint="Escribe tu accion o pregunta...",
                        width=CHAT_W - 92,
                        height=46,
                        multiline=False,
                        on_enter=True,
                        callback=lambda s, a: send_message(),
                    )
                    send_btn = dpg.add_button(
                        tag="send_btn", label="Enviar",
                        width=84, height=46,
                        callback=send_message,
                    )
                    dpg.bind_item_theme(send_btn, state["send_theme"])

            dpg.add_spacer(width=4)

            # ══ DERECHA: log + estado ══
            with dpg.child_window(width=COL_R, height=PANEL_H, border=True):
                dpg.add_spacer(height=4)
                with dpg.tab_bar():

                    with dpg.tab(label="Log"):
                        dpg.add_spacer(height=4)
                        dpg.add_separator()
                        dpg.add_spacer(height=3)
                        with dpg.child_window(tag="log_content",
                                              height=PANEL_H - 160,
                                              border=False):
                            dim_text("Sin eventos.")
                        dpg.add_spacer(height=4)
                        dpg.add_button(label="Exportar log", width=-1,
                                       callback=export_session_log)
                        dpg.add_spacer(height=3)
                        dpg.add_button(
                            label="Limpiar log", width=-1,
                            callback=lambda: (state["session_log"].clear(),
                                             refresh_log()),
                        )
                        dpg.add_spacer(height=3)
                        dpg.add_button(
                            label="Nueva sesion", width=-1,
                            callback=lambda: (
                                export_session_log(silent=True),
                                state.update({"messages": [], "character": {},
                                              "session_log": [], "phase": "idle",
                                              "last_dice_result": None,
                                              "session_number": state.get("session_number", 1) + 1}),
                                dpg.delete_item("chat_scroll", children_only=True),
                                refresh_character_panel(),
                                refresh_log(),
                                refresh_estado_panel(),
                            ),
                        )

                    with dpg.tab(label="Estado"):
                        dpg.add_spacer(height=4)
                        dpg.add_separator()
                        dpg.add_spacer(height=3)
                        with dpg.child_window(tag="estado_content",
                                              height=PANEL_H - 160,
                                              border=False):
                            dim_text("Cargando estado...")
                        dpg.add_spacer(height=4)
                        dpg.add_button(label="Actualizar", width=-1,
                                       callback=refresh_estado_panel)
                        dpg.add_spacer(height=3)
                        dpg.add_button(tag="world_advance_btn",
                                       label="Avanzar Mundo", width=-1,
                                       callback=run_world_agent)

    dpg.set_primary_window("main_window", True)
    refresh_estado_panel()

# ─────────────────────────────────────────────
#  MAIN
# ─────────────────────────────────────────────
def _init_vault_writer():
    global _vault_writer
    if not _AGENT_MODE:
        return
    try:
        config = _orchestrator.config if _orchestrator else {}
        vault_path = config.get("vault", {}).get("path", "vault")
        live = config.get("vault", {}).get("live_updates", True)
        if not live:
            return
        _vault_writer = VaultWriter(vault_path=vault_path)
        session_n = state.get("session_number", 1)
        _vault_writer.start_session(
            session_number=session_n,
            system_name=state.get("system_name", ""),
            campaign_name=state.get("campaign_name", ""),
        )
        print(f"✓ Vault writer activo — vault/Sesiones/Sesion_{session_n:02d}_*.md")
    except Exception as e:
        print(f"⚠ Vault writer no disponible: {e}")


def main():
    print("╔══════════════════════════════════╗")
    print("║       AI NARRATOR v0.2           ║")
    print("║  Motor de Rol con Agentes+Ollama ║")
    print("╚══════════════════════════════════╝")
    print()

    try:
        r = requests.get(f"{OLLAMA_URL}/api/tags", timeout=3)
        models = [m["name"] for m in r.json().get("models", [])]
        print(f"✓ Ollama conectado. Modelos: {', '.join(models) if models else 'ninguno'}")
        if models:
            state["model"] = models[0]
    except Exception as e:
        print("⚠ No se encontró Ollama en localhost:11434")
        print("  Instalar: https://ollama.com")
        print("  Luego: ollama pull llama3.2")
        print()

    if session_manager.load_session(state):
        print("✓ Sesión anterior cargada")

    _init_vault_writer()

    build_gui()

    while dpg.is_dearpygui_running():
        try:
            while True:
                _ui_queue.get_nowait()()
        except _queue_mod.Empty:
            pass
        dpg.render_dearpygui_frame()

    dpg.destroy_context()
    print("Sesión finalizada.")
