"""Tests del parser de planillas (extracción de JSON de respuestas del LLM)."""

from narrator.core.sheet_parser import extract_json_block, parse_character_sheet


def test_extract_json_fenced():
    raw = 'Acá está:\n```json\n{"nombre": "Lucien", "clan": "Toreador"}\n```\nListo.'
    data = extract_json_block(raw)
    assert data == {"nombre": "Lucien", "clan": "Toreador"}


def test_extract_json_sin_fence():
    raw = 'El personaje es {"nombre": "Kael", "clase": "Mago", "nivel": 3}'
    data = extract_json_block(raw)
    assert data["nombre"] == "Kael"
    assert data["nivel"] == 3


def test_extract_json_anidado():
    raw = '{"nombre": "Ana", "atributos": {"fuerza": 3, "destreza": 2}}'
    data = extract_json_block(raw)
    assert data["atributos"]["fuerza"] == 3


def test_extract_json_invalido():
    assert extract_json_block("no hay json acá") is None
    assert extract_json_block("") is None
    assert extract_json_block(None) is None


def test_extract_json_lista_no_es_personaje():
    # Una lista JSON no es una hoja de personaje válida
    assert extract_json_block("[1, 2, 3]") is None


class _FakeLLM:
    def __init__(self, response):
        self._response = response

    def chat(self, messages):
        return self._response


def test_parse_character_sheet_ok():
    llm = _FakeLLM('```json\n{"nombre": "Mira", "ocupacion": "Detective"}\n```')
    char = parse_character_sheet("texto de planilla", llm, system_name="CoC 7e")
    assert char == {"nombre": "Mira", "ocupacion": "Detective"}


def test_parse_character_sheet_respuesta_basura():
    llm = _FakeLLM("no puedo hacer eso")
    assert parse_character_sheet("texto", llm) is None


def test_parse_character_sheet_llm_falla():
    class _BrokenLLM:
        def chat(self, messages):
            raise ConnectionError("ollama caído")

    assert parse_character_sheet("texto", _BrokenLLM()) is None
