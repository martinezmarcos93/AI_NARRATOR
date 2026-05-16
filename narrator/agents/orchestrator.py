"""
Orchestrator — coordina agentes y construye el contexto correcto para cada llamada al LLM.
Es Python puro: no hace llamadas al LLM, solo decide QUÉ contexto armar y QUIÉN habla.
"""

import yaml
from narrator.logger import logger
from pathlib import Path
from narrator.core.prompt_builder import PromptBuilder
from narrator.core.retriever import VaultRetriever
from narrator.core.state_manager import StateManager
from narrator.core.theory_engine import MasterMoveEngine, PacingToneAgent, WorldSimulationEngine, InvestigationEngine

_THEORY_ENGINE_PATH = Path(__file__).parent.parent / "core" / "theory_engine"


class Orchestrator:
    def __init__(self, config_path: str = "./config/config.yaml"):
        self.config = self._load_config(config_path)

        systems_path = self.config.get("systems_path", "data/systems")
        vault_path = self.config.get("vault", {}).get("path", "./vault")
        state_path = self.config.get("estado", {}).get("path", "./estado_campana.yaml")

        self.builder = PromptBuilder(systems_path=systems_path)
        self.retriever = VaultRetriever(vault_path=vault_path)
        self.state = StateManager(state_path=state_path)
        self.state.load()

        self.master_moves = MasterMoveEngine(config_path=_THEORY_ENGINE_PATH)
        self.pacing_agent = PacingToneAgent(config_path=_THEORY_ENGINE_PATH)
        self.world_sim = WorldSimulationEngine(
            config_path=_THEORY_ENGINE_PATH,
            vault_path=Path(vault_path),
        )
        self.investigation = InvestigationEngine(
            config_path=_THEORY_ENGINE_PATH,
            vault_path=Path(vault_path),
        )
        self._investigation_quiet_turns: int = 0

    def _load_config(self, path: str) -> dict:
        try:
            with open(path, encoding="utf-8") as f:
                return yaml.safe_load(f) or {}
        except Exception as e:
            return {}

    # ── Theory engine ─────────────────────────────────────────
    def get_world_status_text(self) -> str:
        """Resumen del WorldSimulationEngine para el system prompt."""
        status = self.world_sim.get_world_status()
        lines = []
        critical = status.get("critical_fronts", {})
        if critical:
            lines.append("Frentes críticos: " + ", ".join(
                f"{n} (etapa {s})" for n, s in critical.items()
            ))
        rep = status.get("reputation", {})
        if rep:
            lines.append("Reputación: " + ", ".join(
                f"{f}: {v:+d}" for f, v in rep.items()
            ))
        events = status.get("recent_events", [])
        if events:
            lines.append("Eventos recientes:\n" + "\n".join(f"  - {e}" for e in events[-3:]))
        return "\n".join(lines)

    def get_investigation_hint(self, app_state: dict) -> str:
        """
        Aplica la Regla de los 3 indicios.
        Devuelve una instrucción para el narrador si los jugadores llevan
        varios turnos sin avanzar en un misterio activo; cadena vacía si todo fluye.
        """
        ultimo = app_state.get("ultimo_evento", "dialogo")
        if ultimo in ("exploracion", "dialogo"):
            self._investigation_quiet_turns += 1
        else:
            self._investigation_quiet_turns = 0

        context = {"quiet_turns": self._investigation_quiet_turns}
        blockade = self.investigation.check_for_blockade(context)
        if not blockade:
            summary = self.investigation.get_active_mysteries_summary()
            return f"Misterios activos:\n{summary}" if summary else ""

        mystery_id = blockade["mystery_id"]
        stall = self.investigation.resolve_stall(mystery_id)
        self._investigation_quiet_turns = 0  # reset tras sugerir pista
        return (
            f"REGLA DE LOS 3 INDICIOS — los jugadores llevan varios turnos sin avanzar.\n"
            f"Pista sugerida para '{mystery_id}': {stall.get('description', '')}\n"
            f"Instrucción: {stall.get('instruction', '')}"
        )

    def record_event(self, event_type: str, intensity: int = 1) -> None:
        """Registra un evento de sesión (llamar desde app.py tras cada turno)."""
        self.pacing_agent.update_event_history(event_type, intensity)

    def _build_move_context(self, app_state: dict, active_fronts: str, active_npcs: str) -> dict:
        relojes = self.state.data.get("relojes", {})
        relojes_por_estallar = sum(
            1 for c in relojes.values()
            if c.get("llenos", 0) >= c.get("segmentos", 6) - 1
        )
        return {
            "tirada_resultado": app_state.get("last_dice_result"),
            "tiempo_sin_accion": 0,
            "frente_activo": bool(active_fronts),
            "jugadores_bloqueados": app_state.get("jugadores_bloqueados", False),
            "peligro_inminente": relojes_por_estallar > 0,
            "ultimo_evento": app_state.get("ultimo_evento", "dialogo"),
            "sesion_tiempo_total": self.state.get_session_number(),
            "relojes_por_estallar": relojes_por_estallar,
            "pnj_en_escena": bool(active_npcs),
        }

    # ── Sistema activo ────────────────────────────────────────
    def get_active_system(self, app_state: dict) -> str:
        if app_state.get("system_slug"):
            return app_state["system_slug"]
        return self.config.get("sistema_activo", "generic")

    def detect_and_set_system(self, text: str, app_state: dict) -> str:
        slug = self.builder.detect_system_from_text(text)
        app_state["system_slug"] = slug
        return slug

    # ── Context builders ──────────────────────────────────────
    def _get_last_user_message(self, app_state: dict) -> str:
        messages = app_state.get("messages", [])
        for msg in reversed(messages):
            if msg.get("role") == "user":
                return msg["content"]
        return ""

    def build_narrator_context(self, app_state: dict) -> str:
        system_slug = self.get_active_system(app_state)
        last_user_msg = self._get_last_user_message(app_state)

        vault_ctx = ""
        if not self.retriever.vault_is_empty():
            if last_user_msg:
                vault_ctx = self.retriever.get_relevant_context(last_user_msg, max_words=300)
            if not vault_ctx:
                vault_ctx = self.retriever.get_relevant_context("escena NPC frente", max_words=300)

        if not vault_ctx:
            manual_text = app_state.get("manual_text", "")
            if manual_text:
                vault_ctx = manual_text[:1500]

        active_npcs = self.retriever.get_active_npcs_summary(max_npcs=6)
        active_fronts = self.retriever.get_active_fronts_summary()
        clocks = self.state.get_clocks_summary()

        pacing_result = self.pacing_agent.tick()
        move_ctx = self._build_move_context(app_state, active_fronts, active_npcs)
        master_move = self.master_moves.select_move(move_ctx)
        world_status = self.get_world_status_text()
        investigation_hint = self.get_investigation_hint(app_state)

        return self.builder.build_narrator_prompt(
            system_slug=system_slug,
            vault_context=vault_ctx,
            character=app_state.get("character") or None,
            last_session=self.state.get_last_session_summary(),
            scene_location=self.state.get_location() or "",
            active_npcs=active_npcs,
            active_fronts=active_fronts,
            clocks_summary=clocks,
            pacing_instruction=pacing_result["instruction"],
            master_move=master_move,
            world_status=world_status,
            investigation_hint=investigation_hint,
        )

    def build_char_creation_context(self, app_state: dict) -> str:
        system_slug = self.get_active_system(app_state)
        manual_text = app_state.get("manual_text", "")
        return self.builder.build_char_creation_prompt(
            system_slug=system_slug,
            manual_excerpt=manual_text,
        )

    # ── Dispatch principal ────────────────────────────────────
    def get_context_for_phase(self, app_state: dict) -> str:
        """
        Punto de entrada principal. Devuelve el system prompt correcto
        según la fase actual de la sesión.
        """
        phase = app_state.get("phase", "idle")
        if phase == "char_creation":
            return self.build_char_creation_context(app_state)
        return self.build_narrator_context(app_state)
