"""Tests de fronts reactivos (C3): relojes en vivo + interrupción forzosa."""

import pytest

from narrator import PROJECT_ROOT
from narrator.agents.extractor_agent import _front_frontmatter
from narrator.core.prompt_builder import PromptBuilder
from narrator.core.state_manager import StateManager


class _FakeRetriever:
    def __init__(self, fronts):
        self._fronts = fronts

    def get_by_type(self, tipo, max_files=10):
        return self._fronts if tipo == "frente" else []


def _front(nombre, reactivo_a=None, escasez="seguridad"):
    return {"meta": {"tipo": "frente", "nombre": nombre, "escasez": escasez,
                     "reactivo_a": reactivo_a or []},
            "body": "", "path": f"{nombre}.md"}


class _Orq:
    """Réplica mínima del wiring del Orchestrator para _react_fronts."""

    # Se toma el método real para no duplicar la lógica bajo test.
    from narrator.agents.orchestrator import Orchestrator as _O
    _react_fronts = _O._react_fronts

    def __init__(self, state, fronts):
        self.state = state
        self.retriever = _FakeRetriever(fronts)
        self._pending_interruption = ""


@pytest.fixture
def state(tmp_path):
    return StateManager(state_path=str(tmp_path / "estado.yaml"))


# ── Avance reactivo ───────────────────────────────────────────
def test_evento_avanza_frente_reactivo(state):
    orq = _Orq(state, [_front("La Cacería", reactivo_a=["combate", "persecucion"])])
    orq._react_fronts("combate", 2)
    assert state.data["relojes"]["La Cacería"]["llenos"] == 1


def test_evento_no_afecta_frente_no_reactivo(state):
    orq = _Orq(state, [_front("La Cacería", reactivo_a=["persecucion"])])
    orq._react_fronts("combate", 2)
    assert "La Cacería" not in state.data["relojes"]


def test_intensidad_alta_avanza_doble(state):
    orq = _Orq(state, [_front("Pánico", reactivo_a=["horror"])])
    orq._react_fronts("horror", 3)
    assert state.data["relojes"]["Pánico"]["llenos"] == 2


def test_reloj_lleno_dispara_interrupcion_una_vez(state):
    orq = _Orq(state, [_front("La Cacería", reactivo_a=["combate"])])
    state.add_front("La Cacería", max_stage=2)
    orq._react_fronts("combate", 1)
    assert orq._pending_interruption == ""
    orq._react_fronts("combate", 1)                    # 2/2 → lleno
    assert orq._pending_interruption == "La Cacería"
    orq._pending_interruption = ""
    orq._react_fronts("combate", 1)                    # ya estaba lleno
    assert orq._pending_interruption == ""


# ── Prompt del evento forzoso ─────────────────────────────────
def test_forced_event_en_prompt():
    pb = PromptBuilder(systems_path=str(PROJECT_ROOT / "data" / "systems"))
    prompt = pb.build_narrator_prompt("generic", forced_event="La Cacería")
    assert "EVENTO FORZOSO" in prompt
    assert "La Cacería" in prompt
    assert "INTERRUMPÍ" in prompt


def test_sin_forced_event_no_hay_seccion():
    pb = PromptBuilder(systems_path=str(PROJECT_ROOT / "data" / "systems"))
    assert "EVENTO FORZOSO" not in pb.build_narrator_prompt("generic")


# ── Frontmatter del extractor ─────────────────────────────────
def test_frontmatter_reactivo_valido():
    fm = _front_frontmatter({"nombre": "La Cacería",
                             "reactivo_a": ["combate", "volar", "persecucion"]})
    assert 'reactivo_a: ["combate", "persecucion"]' in fm   # 'volar' filtrado


def test_frontmatter_sin_reactivo():
    assert "reactivo_a" not in _front_frontmatter({"nombre": "X"})
    assert "reactivo_a" not in _front_frontmatter({"nombre": "X", "reactivo_a": "combate"})
