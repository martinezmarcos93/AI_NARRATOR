"""Tests del ExtractorAgent: parseo tolerante y field-locking en regenerate_npc."""

from narrator.agents.extractor_agent import (
    ExtractorAgent,
    _npc_frontmatter,
    _parse_json_object_response,
    _parse_json_response,
)


class _FakeLLM:
    def __init__(self, response: str):
        self._response = response

    def chat(self, messages, max_tokens=None):
        return self._response


# ── _parse_json_response (array) tolera JSON dañado vía json_repair ──
def test_parse_json_response_con_coma_colgante():
    texto = '```json\n[{"nombre": "Kael"}, {"nombre": "Mira"},]\n```'
    assert _parse_json_response(texto) == [{"nombre": "Kael"}, {"nombre": "Mira"}]


def test_parse_json_response_vacio_si_irrecuperable():
    assert _parse_json_response("no hay nada de json acá") == []


# ── _parse_json_object_response (objeto único) ──────────────────
def test_parse_json_object_response_con_truncamiento():
    texto = '```json\n{"nombre": "Kael", "clase": "Mago"\n```'
    assert _parse_json_object_response(texto) == {"nombre": "Kael", "clase": "Mago"}


def test_parse_json_object_response_none_si_irrecuperable():
    assert _parse_json_object_response("sin json") is None


# ── regenerate_npc: field-locking ────────────────────────────────
def test_regenerate_npc_respeta_campos_fijados():
    llm = _FakeLLM('{"nombre": "Kael el Errante", "clan": "Ventrue", "rol": "espía"}')
    agent = ExtractorAgent(llm=llm, builder=None)
    npc_original = {"nombre": "Kael", "clan": "Nosferatu", "rol": "mendigo"}

    resultado = agent.regenerate_npc(npc_original, locked_fields={"clan": "Nosferatu"})

    # El LLM "intentó" cambiar el clan a Ventrue, pero locked_fields lo fuerza de vuelta.
    assert resultado["clan"] == "Nosferatu"
    assert resultado["nombre"] == "Kael el Errante"
    assert resultado["rol"] == "espía"


def test_regenerate_npc_sin_locked_fields():
    llm = _FakeLLM('{"nombre": "Ana", "clase": "Pícara"}')
    agent = ExtractorAgent(llm=llm, builder=None)
    resultado = agent.regenerate_npc({"nombre": "Ana"})
    assert resultado == {"nombre": "Ana", "clase": "Pícara"}


def test_regenerate_npc_respuesta_no_parseable_devuelve_none():
    llm = _FakeLLM("no puedo generar eso")
    agent = ExtractorAgent(llm=llm, builder=None)
    assert agent.regenerate_npc({"nombre": "Kael"}) is None


# ── _npc_frontmatter: metadata de token (Fase 8) ─────────────────
def test_npc_frontmatter_amenaza_alta_color_rojo():
    fm = _npc_frontmatter({"nombre": "Kael", "amenaza": "alta"}, "generic")
    assert 'color: "rojo"' in fm
    assert 'icono: "🔴"' in fm
    assert 'estado: "vivo"' in fm
    assert "condiciones: []" in fm


def test_npc_frontmatter_sin_amenaza_usa_defaults():
    fm = _npc_frontmatter({"nombre": "Kael"}, "generic")
    assert 'color: "gris"' in fm
    assert 'icono: "⚪"' in fm


def test_npc_frontmatter_amenaza_media_y_baja():
    fm_media = _npc_frontmatter({"nombre": "Kael", "amenaza": "media"}, "generic")
    fm_baja = _npc_frontmatter({"nombre": "Kael", "amenaza": "baja"}, "generic")
    assert 'color: "amarillo"' in fm_media
    assert 'color: "verde"' in fm_baja
