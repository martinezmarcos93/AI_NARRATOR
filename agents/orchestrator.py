"""
Orchestrator — coordina agentes y construye el contexto correcto para cada llamada al LLM.
Es Python puro: no hace llamadas al LLM, solo decide QUÉ contexto armar y QUIÉN habla.
"""

import yaml
from pathlib import Path
from core.prompt_builder import PromptBuilder
from core.retriever import VaultRetriever
from core.state_manager import StateManager


class Orchestrator:
    def __init__(self, config_path: str = "./config.yaml"):
        self.config = self._load_config(config_path)

        systems_path = self.config.get("systems_path", "./systems")
        vault_path = self.config.get("vault", {}).get("path", "./vault")
        state_path = self.config.get("estado", {}).get("path", "./estado_campana.yaml")

        self.builder = PromptBuilder(systems_path=systems_path)
        self.retriever = VaultRetriever(vault_path=vault_path)
        self.state = StateManager(state_path=state_path)
        self.state.load()

    def _load_config(self, path: str) -> dict:
        try:
            with open(path, encoding="utf-8") as f:
                return yaml.safe_load(f) or {}
        except Exception:
            return {}

    # ── Sistema activo ────────────────────────────────────────
    def get_active_system(self, app_state: dict) -> str:
        """
        Prioridad: app_state["system_slug"] > config.yaml > "generic"
        app_state["system_slug"] se setea cuando el usuario carga un PDF.
        """
        if app_state.get("system_slug"):
            return app_state["system_slug"]
        return self.config.get("sistema_activo", "generic")

    def detect_and_set_system(self, text: str, app_state: dict) -> str:
        """Detecta el sistema desde texto de PDF y lo guarda en app_state."""
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
        """Construye el system prompt completo para el agente narrador."""
        system_slug = self.get_active_system(app_state)
        last_user_msg = self._get_last_user_message(app_state)

        # Contexto del vault (relevante a lo que dijo el jugador)
        vault_ctx = ""
        if not self.retriever.vault_is_empty():
            if last_user_msg:
                vault_ctx = self.retriever.get_relevant_context(last_user_msg, max_words=300)
            if not vault_ctx:
                vault_ctx = self.retriever.get_relevant_context("escena NPC frente", max_words=300)

        # Si no hay vault todavía, usar excerpt del manual PDF
        if not vault_ctx:
            manual_text = app_state.get("manual_text", "")
            if manual_text:
                vault_ctx = manual_text[:1500]

        active_npcs = self.retriever.get_active_npcs_summary(max_npcs=6)
        active_fronts = self.retriever.get_active_fronts_summary()
        clocks = self.state.get_clocks_summary()

        return self.builder.build_narrator_prompt(
            system_slug=system_slug,
            vault_context=vault_ctx,
            character=app_state.get("character") or None,
            last_session=self.state.get_last_session_summary(),
            scene_location=self.state.get_location() or "",
            active_npcs=active_npcs,
            active_fronts=active_fronts,
            clocks_summary=clocks,
        )

    def build_char_creation_context(self, app_state: dict) -> str:
        """Construye el system prompt para la fase de creación de personaje."""
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
        # idle o playing → narrador
        return self.build_narrator_context(app_state)
