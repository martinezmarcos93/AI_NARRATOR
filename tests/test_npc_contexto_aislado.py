"""Test Fase 12: el contexto de decisión de un NPC no debe filtrar
relojes de Frentes ni el resumen de la última sesión (secretos del Máster)."""

from narrator.agents.npc_routines import NPCRoutinesAgent
from narrator.core.state_manager import StateManager


def test_world_state_summary_no_filtra_relojes_ni_resumen_sesion(tmp_path):
    state = StateManager(state_path=str(tmp_path / "estado.yaml"))
    state.set_location("El Muelle Viejo")
    state.add_clock("El Ritual Oscuro", segments=6, description="secreto del culto")
    state.add_session_summary("Los PJs descubrieron que el alcalde es un impostor.")

    agent = NPCRoutinesAgent(llm=None, builder=None, state=state)
    summary = agent._build_world_state_summary("generic")

    assert "El Muelle Viejo" in summary
    assert "El Ritual Oscuro" not in summary
    assert "impostor" not in summary
    assert "secreto del culto" not in summary
