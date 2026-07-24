"""Tests del NarratorAgent — post-procesamiento de respuestas del narrador."""

from narrator.agents.narrator_agent import NarratorAgent


def _agent() -> NarratorAgent:
    return NarratorAgent()


# ── extract_dice_suggestion (Fase 2: tirada sugerida pendiente) ─
def test_sugerencia_pool_d10():
    texto = "Tirá 5d10 para resistir el ataque."
    assert _agent().extract_dice_suggestion(texto) == (5, 10)


def test_sugerencia_d20_con_modificador():
    texto = "Hacé una tirada de 1D20+3 contra la CD."
    assert _agent().extract_dice_suggestion(texto) == (1, 20)


def test_sugerencia_con_espacio_entre_cantidad_y_d():
    texto = "Tirá 3 d6 de daño."
    assert _agent().extract_dice_suggestion(texto) == (3, 6)


def test_sugerencia_d100_percentil():
    texto = "Hacé tu tirada de Cordura: 1d100 contra tu POD."
    assert _agent().extract_dice_suggestion(texto) == (1, 100)


def test_sin_sugerencia_devuelve_none():
    texto = "El guardia te mira con desconfianza y no dice nada."
    assert _agent().extract_dice_suggestion(texto) is None


def test_caras_no_soportadas_devuelve_none():
    texto = "Tirá 2d3 para ver el resultado."
    assert _agent().extract_dice_suggestion(texto) is None


def test_cantidad_fuera_de_rango_devuelve_none():
    texto = "Tirá 99d10 en un ritual masivo."
    assert _agent().extract_dice_suggestion(texto) is None


def test_toma_la_primera_sugerencia_si_hay_varias():
    texto = "Primero probá 2d6, y si falla vas a necesitar 1d20 extra."
    assert _agent().extract_dice_suggestion(texto) == (2, 6)
