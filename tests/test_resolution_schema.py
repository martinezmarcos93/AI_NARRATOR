"""Tests de validación del bloque `resolution:` de los YAML de sistema."""

import pytest
import yaml

from narrator import PROJECT_ROOT
from narrator.core.resolution_schema import ResolutionSchemaError, validate_resolution


# ── los 5 sistemas reales del proyecto deben validar limpio ──────
@pytest.mark.parametrize(
    "slug", ["dnd_5e", "vtm_v20", "coc_7e", "pathfinder_2e", "generic"]
)
def test_sistemas_reales_validan_ok(slug):
    path = PROJECT_ROOT / "data" / "systems" / f"{slug}.yaml"
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    validate_resolution(data["resolution"], system_slug=slug)  # no debe lanzar


# ── casos válidos mínimos por mecánica ────────────────────────────
def _valido_d20():
    return {
        "mecanica": "d20_vs_dc",
        "dificultades": {"normal": 15},
        "dificultad_default": "normal",
        "atributo_default": "destreza",
        "acciones": [{"keywords": ["ataco"], "atributo": "fuerza", "etiqueta": "Fuerza"}],
    }


def test_d20_vs_dc_valido_no_lanza():
    validate_resolution(_valido_d20())


def test_ratio_valido_no_lanza():
    validate_resolution({"mecanica": "ratio", "bandas": {"exito": 0.8, "parcial": 0.5}})


# ── errores generales ──────────────────────────────────────────
def test_no_es_dict():
    with pytest.raises(ResolutionSchemaError, match="esperado un objeto"):
        validate_resolution([])


def test_falta_mecanica():
    with pytest.raises(ResolutionSchemaError, match="mecanica"):
        validate_resolution({})


def test_mecanica_desconocida():
    with pytest.raises(ResolutionSchemaError, match="desconocida"):
        validate_resolution({"mecanica": "carta_de_tarot"})


# ── mecánicas con escalera de dificultades (d20/pool_d10/percentil) ──
def test_falta_dificultades():
    res = _valido_d20()
    del res["dificultades"]
    with pytest.raises(ResolutionSchemaError, match="dificultades"):
        validate_resolution(res)


def test_dificultades_vacio():
    res = _valido_d20()
    res["dificultades"] = {}
    with pytest.raises(ResolutionSchemaError, match="dificultades"):
        validate_resolution(res)


def test_dificultad_default_no_existe_en_dificultades():
    res = _valido_d20()
    res["dificultad_default"] = "imposible"
    with pytest.raises(ResolutionSchemaError, match="dificultad_default"):
        validate_resolution(res)


def test_dificultades_tipo_incorrecto():
    res = _valido_d20()
    res["dificultades"] = "no es un dict"
    with pytest.raises(ResolutionSchemaError, match="dict"):
        validate_resolution(res)


def test_falta_atributo_default():
    res = _valido_d20()
    del res["atributo_default"]
    with pytest.raises(ResolutionSchemaError, match="atributo_default"):
        validate_resolution(res)


def test_falta_acciones():
    res = _valido_d20()
    del res["acciones"]
    with pytest.raises(ResolutionSchemaError, match="acciones"):
        validate_resolution(res)


def test_acciones_vacio():
    res = _valido_d20()
    res["acciones"] = []
    with pytest.raises(ResolutionSchemaError, match="acciones"):
        validate_resolution(res)


def test_accion_sin_keywords():
    res = _valido_d20()
    res["acciones"] = [{"atributo": "fuerza", "etiqueta": "Fuerza"}]
    with pytest.raises(ResolutionSchemaError, match="keywords"):
        validate_resolution(res)


def test_accion_keywords_vacio():
    res = _valido_d20()
    res["acciones"] = [{"keywords": [], "atributo": "fuerza", "etiqueta": "Fuerza"}]
    with pytest.raises(ResolutionSchemaError, match="keywords"):
        validate_resolution(res)


def test_accion_no_es_dict():
    res = _valido_d20()
    res["acciones"] = ["no es un dict"]
    with pytest.raises(ResolutionSchemaError, match="acciones\\[0\\]"):
        validate_resolution(res)


def test_keywords_dificultad_opcional_tipo_incorrecto():
    res = _valido_d20()
    res["keywords_dificultad"] = "no es un dict"
    with pytest.raises(ResolutionSchemaError, match="keywords_dificultad"):
        validate_resolution(res)


def test_keywords_dificultad_ausente_es_valido():
    res = _valido_d20()
    assert "keywords_dificultad" not in res
    validate_resolution(res)  # no debe lanzar — es opcional


# ── mecánica ratio ────────────────────────────────────────────
def test_ratio_falta_bandas():
    with pytest.raises(ResolutionSchemaError, match="bandas"):
        validate_resolution({"mecanica": "ratio"})


def test_ratio_bandas_vacio():
    with pytest.raises(ResolutionSchemaError, match="bandas"):
        validate_resolution({"mecanica": "ratio", "bandas": {}})


# ── pool_d10 y percentil comparten schema con d20_vs_dc ──────────
def test_pool_d10_valido():
    res = _valido_d20()
    res["mecanica"] = "pool_d10"
    validate_resolution(res)


def test_percentil_valido():
    res = _valido_d20()
    res["mecanica"] = "percentil"
    validate_resolution(res)


def test_pool_d10_hereda_validacion_de_dificultades():
    res = _valido_d20()
    res["mecanica"] = "pool_d10"
    del res["dificultades"]
    with pytest.raises(ResolutionSchemaError, match="dificultades"):
        validate_resolution(res)
