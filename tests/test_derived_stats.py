"""Tests del DSL de estadísticas derivadas — sin eval/exec, vocabulario fijo."""

import pytest

from narrator.core.derived_stats import (
    DerivedStatError,
    evaluate,
    evaluate_all,
    register_computer,
)


# ── copy_of ────────────────────────────────────────────────────
def test_copy_of():
    assert evaluate({"copy_of": "fuerza"}, {"fuerza": 16}) == 16


def test_copy_of_campo_desconocido():
    with pytest.raises(DerivedStatError):
        evaluate({"copy_of": "carisma"}, {"fuerza": 16})


# ── half_of ─────────────────────────────────────────────────────
def test_half_of_floor_por_defecto():
    assert evaluate({"half_of": "sangre_max"}, {"sangre_max": 9}) == 4


def test_half_of_ceil():
    assert evaluate({"half_of": "sangre_max", "round": "ceil"}, {"sangre_max": 9}) == 5


# ── floor_div (caso real: modificador de atributo D&D/PF2e) ────
def test_floor_div_modificador_dnd():
    # score 16 -> (16-10)//2 = +3
    spec = {"floor_div": "fuerza", "divisor": 2, "offset": -10}
    assert evaluate(spec, {"fuerza": 16}) == 3


def test_floor_div_modificador_negativo():
    # score 7 -> (7-10)//2 = -2 (floor negativo, no truncado hacia 0)
    spec = {"floor_div": "destreza", "divisor": 2, "offset": -10}
    assert evaluate(spec, {"destreza": 7}) == -2


def test_floor_div_divisor_cero():
    with pytest.raises(DerivedStatError):
        evaluate({"floor_div": "fuerza", "divisor": 0}, {"fuerza": 16})


# ── sum_of ──────────────────────────────────────────────────────
def test_sum_of():
    spec = {"sum_of": ["fuerza", "destreza", "resistencia"]}
    assert evaluate(spec, {"fuerza": 3, "destreza": 2, "resistencia": 4}) == 9


def test_sum_of_lista_vacia():
    with pytest.raises(DerivedStatError):
        evaluate({"sum_of": []}, {"fuerza": 1})


# ── computer (registro nombrado, sin eval) ──────────────────────
def test_computer_registrado():
    register_computer("doble_fuerza")(lambda data: data["fuerza"] * 2)
    assert evaluate({"computer": "doble_fuerza"}, {"fuerza": 5}) == 10


def test_computer_no_registrado():
    with pytest.raises(DerivedStatError):
        evaluate({"computer": "no_existe_xyz"}, {"fuerza": 5})


# ── errores generales ────────────────────────────────────────────
def test_spec_vacia_invalida():
    with pytest.raises(DerivedStatError):
        evaluate({}, {"fuerza": 5})


def test_operador_desconocido():
    with pytest.raises(DerivedStatError):
        evaluate({"multiply_by": "fuerza"}, {"fuerza": 5})


def test_campo_no_numerico():
    with pytest.raises(DerivedStatError):
        evaluate({"floor_div": "nombre", "divisor": 2}, {"nombre": "Kael"})


# ── evaluate_all: encadenamiento de derivados ───────────────────
def test_evaluate_all_encadena_derivados():
    specs = {
        "mod_fuerza": {"floor_div": "fuerza", "divisor": 2, "offset": -10},
        "mod_fuerza_doble": {"sum_of": ["mod_fuerza", "mod_fuerza"]},
    }
    result = evaluate_all(specs, {"fuerza": 16})
    assert result == {"mod_fuerza": 3, "mod_fuerza_doble": 6}
