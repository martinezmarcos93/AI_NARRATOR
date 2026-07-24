"""Tests del PlayerAgent y el harness de playtest IA-vs-IA (Fase 20)."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from playtest import detect_secret_leak, run_playtest

from narrator.agents.player_agent import ARCHETYPES, PlayerAgent


class _FakeLLM:
    def __init__(self, responses):
        self._responses = list(responses)

    def chat(self, messages, max_tokens=None):
        if not self._responses:
            return "..."
        return self._responses.pop(0) if len(self._responses) > 1 else self._responses[0]


# ── PlayerAgent ────────────────────────────────────────────────
def test_archetype_invalido_lanza_error():
    with pytest.raises(ValueError):
        PlayerAgent(_FakeLLM(["x"]), archetype="no_existe")


def test_decide_action_devuelve_texto_del_llm():
    agent = PlayerAgent(_FakeLLM(["Investigo el cuarto con cuidado."]), archetype="cauteloso")
    assert agent.decide_action("Estás en una habitación oscura.") == "Investigo el cuarto con cuidado."


def test_todos_los_arquetipos_instancian():
    for arch in ARCHETYPES:
        PlayerAgent(_FakeLLM(["x"]), archetype=arch)


# ── detect_secret_leak ────────────────────────────────────────
def test_detecta_fuga_literal():
    assert detect_secret_leak("El alcalde es en realidad un impostor.", ["el alcalde es un impostor"]) is False
    assert detect_secret_leak("El culto oscuro se reúne en la cripta.", ["culto oscuro"]) is True


def test_sin_fuga():
    assert detect_secret_leak("Nada relevante pasa.", ["secreto A", "secreto B"]) is False


def test_sin_secretos_declarados():
    assert detect_secret_leak("Cualquier texto.", []) is False


# ── run_playtest ───────────────────────────────────────────────
def test_run_playtest_cuenta_fugas():
    narrator = _FakeLLM(["El culto oscuro planea algo terrible."])
    player = _FakeLLM(["Investigo con cuidado."])
    result = run_playtest(narrator, player, turns=3, secrets=["culto oscuro"])
    assert result["turns"] == 3
    assert result["leaks"] == 3
    assert result["leak_rate"] == 1.0


def test_run_playtest_sin_fugas():
    narrator = _FakeLLM(["Ves una puerta cerrada al fondo del pasillo."])
    player = _FakeLLM(["Miro alrededor."])
    result = run_playtest(narrator, player, turns=2, secrets=["culto oscuro"])
    assert result["leaks"] == 0
    assert result["leak_rate"] == 0.0


def test_run_playtest_cuenta_dice_first_miss():
    narrator = _FakeLLM(["Conseguís herirlo de un golpe certero."])
    player = _FakeLLM(["Ataco al orco"])
    result = run_playtest(narrator, player, turns=2)
    assert result["dice_first_misses"] == 2
    assert result["dice_first_miss_rate"] == 1.0


def test_run_playtest_cero_turnos_no_rompe():
    result = run_playtest(_FakeLLM(["x"]), _FakeLLM(["x"]), turns=0)
    assert result["leak_rate"] == 0.0
    assert result["dice_first_miss_rate"] == 0.0
