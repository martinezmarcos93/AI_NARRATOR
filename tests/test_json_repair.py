"""Tests de reparación best-effort de JSON malformado devuelto por un LLM."""

from narrator.core.json_repair import repair, try_parse


# ── try_parse: JSON válido se devuelve tal cual, sin tocar reparación ──
def test_json_valido_no_toca_nada():
    assert try_parse('{"nombre": "Kael", "nivel": 3}') == {"nombre": "Kael", "nivel": 3}


# ── coma colgante antes de cierre ──────────────────────────────
def test_coma_colgante_objeto():
    texto = '{"nombre": "Kael", "nivel": 3,}'
    assert try_parse(texto) == {"nombre": "Kael", "nivel": 3}


def test_coma_colgante_array():
    texto = '["a", "b", "c",]'
    assert try_parse(texto) == ["a", "b", "c"]


# ── llaves/corchetes sin cerrar (truncamiento por max_tokens) ──
def test_objeto_truncado_le_falta_llave():
    texto = '{"nombre": "Kael", "clase": "Mago"'
    assert try_parse(texto) == {"nombre": "Kael", "clase": "Mago"}


def test_array_de_objetos_truncado():
    texto = '[{"nombre": "Kael"}, {"nombre": "Mira"'
    resultado = try_parse(texto)
    assert resultado == [{"nombre": "Kael"}, {"nombre": "Mira"}]


def test_no_cuenta_llaves_dentro_de_strings():
    # La descripción narrativa contiene "{" y "}" — no debe confundir el balanceo.
    texto = '{"nombre": "Kael", "descripcion": "Un mercenario que dice {ya vengo}"'
    resultado = try_parse(texto)
    assert resultado["nombre"] == "Kael"
    assert resultado["descripcion"] == "Un mercenario que dice {ya vengo}"


# ── campo numérico con texto pegado ─────────────────────────────
def test_numero_con_texto_pegado():
    texto = '{"nivel_poder": 5 aproximadamente, "nombre": "Kael"}'
    assert try_parse(texto) == {"nivel_poder": 5, "nombre": "Kael"}


# ── combinación de varios daños a la vez ────────────────────────
def test_combinacion_de_danos():
    texto = '{"nombre": "Kael", "nivel": 7 aprox, "clase": "Mago",'
    resultado = try_parse(texto)
    assert resultado == {"nombre": "Kael", "nivel": 7, "clase": "Mago"}


# ── casos irrecuperables ────────────────────────────────────────
def test_texto_vacio_devuelve_none():
    assert try_parse("") is None
    assert try_parse(None) is None


def test_basura_total_devuelve_none():
    assert try_parse("esto no es json ni reparable de ninguna forma") is None


# ── repair() como función de bajo nivel ─────────────────────────
def test_repair_es_idempotente_sobre_json_valido():
    valido = '{"a": 1}'
    assert repair(valido) == valido
