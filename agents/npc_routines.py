"""
NPC Routines Agent — simula el comportamiento de NPCs entre escenas y sesiones.
Cada NPC tiene un pool de acciones. El agente elige según estado del mundo.
"""

from core.llm_client import LLMClient
from core.prompt_builder import PromptBuilder
from core.state_manager import StateManager


class NPCRoutinesAgent:
    def __init__(self, llm: LLMClient, builder: PromptBuilder, state: StateManager):
        self.llm = llm
        self.builder = builder
        self.state = state

    def _build_world_state_summary(self, system_slug: str) -> str:
        """Construye un texto compacto del estado del mundo para dárselo al NPC."""
        location = self.state.get_location() or "locación desconocida"
        session = self.state.get_session_number()
        clocks = self.state.get_clocks_summary()
        last = self.state.get_last_session_summary()

        parts = [
            f"Sesión: {session}",
            f"Locación actual de los PJs: {location}",
        ]
        if last:
            parts.append(f"Última sesión: {last}")
        if clocks:
            parts.append(f"Relojes activos:\n{clocks}")
        return "\n".join(parts)

    def get_npc_action(
        self,
        npc_data: dict,
        system_slug: str,
        world_state: str = "",
    ) -> dict:
        """
        Decide qué hace un NPC dado el estado del mundo.
        npc_data: dict con campos del NPC (nombre, agenda, clan, etc.)
        Devuelve: {"npc": str, "action": str, "description": str}
        """
        if not world_state:
            world_state = self._build_world_state_summary(system_slug)

        prompt = self.builder.build_npc_action_prompt(system_slug, npc_data, world_state)
        response = self.llm.chat(
            [{"role": "user", "content": prompt}],
            max_tokens=80,
        )

        action = "observar y esperar"
        description = f"{npc_data.get('nombre', 'El NPC')} observa la situación."

        if "ACCIÓN:" in response and "DESCRIPCIÓN:" in response:
            parts = response.split("|")
            if len(parts) >= 2:
                action = parts[0].replace("ACCIÓN:", "").strip()
                description = parts[1].replace("DESCRIPCIÓN:", "").strip()

        return {
            "npc": npc_data.get("nombre", "?"),
            "action": action,
            "description": description,
        }

    def simulate_between_sessions(
        self,
        npcs: list[dict],
        system_slug: str,
    ) -> list[dict]:
        """
        Simula lo que hacen los NPCs de alta amenaza entre sesiones.
        npcs: lista de dicts con {"meta": {...}, "body": "..."}
        Devuelve lista de acciones realizadas, y las registra en el estado.
        """
        world_state = self._build_world_state_summary(system_slug)
        results = []

        for npc_entry in npcs:
            meta = npc_entry.get("meta", {})
            # Solo simular NPCs con amenaza alta o media
            if meta.get("amenaza") not in ("alta", "media"):
                continue

            result = self.get_npc_action(meta, system_slug, world_state)
            results.append(result)

            # Registrar en downtime del estado
            self.state.add_active_npc(result["npc"], result["description"])

        if results:
            self.state.save()

        return results
