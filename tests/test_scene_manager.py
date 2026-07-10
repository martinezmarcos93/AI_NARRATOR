"""Tests del sistema de escenas (desbloqueos determinísticos, C2)."""

import pytest

from narrator.core.scene_manager import SceneManager
from narrator.core.state_manager import StateManager


class _FakeRetriever:
    def __init__(self, scenes):
        self._scenes = scenes

    def get_by_type(self, tipo, max_files=50):
        return self._scenes if tipo == "escena" else []


def _scene(nombre, **meta):
    meta.update({"tipo": "escena", "nombre": nombre})
    return {"meta": meta, "body": "", "path": f"{nombre}.md"}


@pytest.fixture
def state(tmp_path):
    return StateManager(state_path=str(tmp_path / "estado.yaml"))


def _mgr(state, scenes):
    return SceneManager(retriever=_FakeRetriever(scenes), state=state)


# ── Desbloqueos ───────────────────────────────────────────────
def test_sin_condiciones_disponible_de_entrada(state):
    mgr = _mgr(state, [_scene("Apertura")])
    result = mgr.evaluate(player_text="hola")
    assert result["desbloqueadas"] == ["Apertura"]
    assert state.get_scene_state("Apertura")["estado"] == "disponible"
    assert state.get_scene_state("Apertura")["desbloqueada_por"] == "inicio"


def test_desbloqueo_por_keyword(state):
    mgr = _mgr(state, [_scene("Emboscada", detectar=["puente", "río"])])
    assert mgr.evaluate(player_text="sigo por el camino")["desbloqueadas"] == []
    result = mgr.evaluate(player_text="Cruzo el puente de piedra")
    assert result["desbloqueadas"] == ["Emboscada"]
    assert "keyword: puente" in state.get_scene_state("Emboscada")["desbloqueada_por"]


def test_desbloqueo_por_reloj_lleno(state):
    state.add_clock("La Horda", segments=2)
    mgr = _mgr(state, [_scene("Asalto final", reloj="La Horda")])
    assert mgr.evaluate()["desbloqueadas"] == []
    state.advance_clock("La Horda", 2)
    assert mgr.evaluate()["desbloqueadas"] == ["Asalto final"]


def test_flags_requeridos_bloquean(state):
    mgr = _mgr(state, [_scene("Audiencia", detectar=["castillo"],
                              requiere_flags=["invitacion"])])
    assert mgr.evaluate(player_text="voy al castillo")["desbloqueadas"] == []
    state.set_flag("invitacion", True)
    assert mgr.evaluate(player_text="voy al castillo")["desbloqueadas"] == ["Audiencia"]


# ── Jugadas y flags otorgados ─────────────────────────────────
def test_jugada_cuando_narrador_la_narra(state):
    mgr = _mgr(state, [_scene("Emboscada", detectar=["puente"],
                              otorga_flags=["emboscada_superada"])])
    mgr.evaluate(player_text="cruzo el puente")           # → disponible
    result = mgr.evaluate(narrator_text="Al llegar al puente, sombras caen sobre vos...")
    assert result["jugadas"] == ["Emboscada"]
    assert state.get_scene_state("Emboscada")["estado"] == "jugada"
    assert state.get_flag("emboscada_superada") is True


def test_no_salta_de_bloqueada_a_jugada_en_un_turno(state):
    mgr = _mgr(state, [_scene("Emboscada", detectar=["puente"])])
    result = mgr.evaluate(player_text="cruzo el puente",
                          narrator_text="el puente cruje bajo tus pies")
    assert result["desbloqueadas"] == ["Emboscada"]
    assert result["jugadas"] == []                        # recién el próximo turno


def test_escena_jugada_no_se_reevalua(state):
    mgr = _mgr(state, [_scene("Apertura")])
    mgr.evaluate()
    state.set_scene_state("Apertura", "jugada")
    result = mgr.evaluate(player_text="cualquier cosa")
    assert result["desbloqueadas"] == [] and result["jugadas"] == []


# ── Secciones de salida ───────────────────────────────────────
def test_prompt_section(state):
    mgr = _mgr(state, [_scene("Apertura"), _scene("Final", detectar=["torre"])])
    result = mgr.evaluate()
    section = mgr.get_prompt_section(result["desbloqueadas"])
    assert "DESBLOQUEADAS AHORA" in section and "Apertura" in section


def test_prompt_section_vacia_sin_escenas(state):
    mgr = _mgr(state, [])
    assert mgr.get_prompt_section([]) == ""


def test_status_summary_ordena_disponibles_primero(state):
    mgr = _mgr(state, [_scene("A"), _scene("B", detectar=["x"])])
    mgr.evaluate()
    summary = mgr.get_status_summary()
    assert summary.splitlines()[0].startswith("▶ A")
