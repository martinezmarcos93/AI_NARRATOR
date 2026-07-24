"""Tests de integración: combate (cola de iniciativa) en StateManager y PromptBuilder."""

import pytest

from narrator.core.prompt_builder import PromptBuilder
from narrator.core.state_manager import StateManager


@pytest.fixture
def state(tmp_path):
    return StateManager(state_path=str(tmp_path / "estado.yaml"))


# ── StateManager: combate ────────────────────────────────────
def test_start_combat_y_current(state):
    state.start_combat([("Goblin", 8), ("Kael", 15), ("Mira", 12)])
    assert state.is_in_combat() is True
    q = state.get_combat_queue()
    assert q.order() == ["Kael", "Mira", "Goblin"]


def test_advance_combat_turn_persiste_estado(state):
    state.start_combat([("Kael", 15), ("Goblin", 8)])
    assert state.advance_combat_turn() == "Goblin"
    # Recargar desde disco: el avance de turno debe haber quedado guardado.
    reloaded = StateManager(state_path=str(state.path))
    reloaded.load()
    assert reloaded.get_combat_queue().current_name() == "Goblin"


def test_end_combat(state):
    state.start_combat([("Kael", 15)])
    state.end_combat()
    assert state.is_in_combat() is False
    assert state.get_combat_queue() is None


def test_advance_combat_turn_sin_combate_activo_devuelve_none(state):
    assert state.advance_combat_turn() is None


def test_get_combat_status_text_sin_combate(state):
    assert state.get_combat_status_text() == ""


def test_get_combat_status_text_con_combate(state):
    state.start_combat([("Kael", 15), ("Goblin", 8)])
    texto = state.get_combat_status_text()
    assert "Ronda 1" in texto
    assert "Kael" in texto
    assert "Turno activo: Kael" in texto


# ── PromptBuilder: sección COMBATE EN CURSO ──────────────────
def test_prompt_incluye_combate_cuando_hay_estado(tmp_path):
    builder = PromptBuilder(systems_path=str(tmp_path))
    # generic.yaml no existe en tmp_path; load_system cae a su propio
    # fallback interno solo si el archivo existe — acá alcanza con
    # construir el prompt pasando el texto ya resuelto de combate.
    (tmp_path / "generic.yaml").write_text(
        'llm_system_prompt: "Sos un narrador."\n', encoding="utf-8"
    )
    prompt = builder.build_narrator_prompt(
        system_slug="generic",
        combat_status="Ronda 2. Orden de iniciativa: Kael, Goblin. Turno activo: Goblin.",
    )
    assert "COMBATE EN CURSO" in prompt
    assert "Turno activo: Goblin" in prompt


def test_prompt_sin_combate_no_incluye_seccion(tmp_path):
    builder = PromptBuilder(systems_path=str(tmp_path))
    (tmp_path / "generic.yaml").write_text(
        'llm_system_prompt: "Sos un narrador."\n', encoding="utf-8"
    )
    prompt = builder.build_narrator_prompt(system_slug="generic")
    assert "COMBATE EN CURSO" not in prompt
