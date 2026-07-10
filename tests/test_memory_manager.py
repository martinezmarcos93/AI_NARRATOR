"""Tests de la memoria episódica jerárquica (MemoryManager)."""

from narrator.core.memory_manager import MemoryManager


def _msgs(n: int) -> list:
    return [{"role": "user" if i % 2 == 0 else "assistant", "content": f"turno {i}"}
            for i in range(n)]


class _FakeLLM:
    def __init__(self, response="- resumen del lote"):
        self.calls = 0
        self._response = response

    def chat(self, messages):
        self.calls += 1
        return self._response


# ── Capa 1: ventana de trabajo ────────────────────────────────
def test_working_window_recorta():
    mm = MemoryManager(working_window=10)
    msgs = _msgs(25)
    window = mm.get_working_messages(msgs)
    assert len(window) == 10
    assert window[-1]["content"] == "turno 24"     # los más recientes


def test_working_window_historial_corto_va_entero():
    mm = MemoryManager(working_window=10)
    msgs = _msgs(6)
    assert mm.get_working_messages(msgs) == msgs


# ── Capa 2: disparo y acumulación de resúmenes ────────────────
def test_no_resume_bajo_umbral():
    mm = MemoryManager(working_window=10, batch_size=10)
    # 15 mensajes: solo 5 fuera de la ventana → lote incompleto
    assert mm.pending_batch(_msgs(15)) == []
    llm = _FakeLLM()
    assert mm.summarize_batch(_msgs(15), llm) is False
    assert llm.calls == 0


def test_resume_al_llegar_al_umbral():
    mm = MemoryManager(working_window=10, batch_size=10)
    msgs = _msgs(20)                                # 10 fuera de la ventana
    assert len(mm.pending_batch(msgs)) == 10
    llm = _FakeLLM("- el jugador entró a la cripta")
    assert mm.summarize_batch(msgs, llm) is True
    assert llm.calls == 1
    assert "cripta" in mm.get_summary_text()
    # El lote quedó consumido: no vuelve a resumir lo mismo
    assert mm.pending_batch(msgs) == []


def test_resumenes_se_acumulan():
    mm = MemoryManager(working_window=10, batch_size=10)
    llm = _FakeLLM("- hechos")
    assert mm.summarize_batch(_msgs(20), llm) is True
    assert mm.summarize_batch(_msgs(30), llm) is True
    assert mm.get_summary_text().count("- hechos") == 2


def test_error_llm_no_avanza_puntero():
    mm = MemoryManager(working_window=10, batch_size=10)
    msgs = _msgs(20)
    assert mm.summarize_batch(msgs, _FakeLLM("[Error LLM: timeout]")) is False
    assert mm.get_summary_text() == ""
    # El lote sigue pendiente para reintentar
    assert len(mm.pending_batch(msgs)) == 10


# ── Ciclo de vida / persistencia ──────────────────────────────
def test_reset():
    mm = MemoryManager(working_window=10, batch_size=10)
    mm.summarize_batch(_msgs(20), _FakeLLM())
    mm.reset()
    assert mm.get_summary_text() == ""
    assert len(mm.pending_batch(_msgs(20))) == 10


def test_persistencia_roundtrip():
    mm = MemoryManager(working_window=10, batch_size=10)
    mm.summarize_batch(_msgs(20), _FakeLLM("- dato clave"))
    data = mm.to_dict()

    mm2 = MemoryManager(working_window=10, batch_size=10)
    mm2.from_dict(data)
    assert mm2.get_summary_text() == "- dato clave"
    assert mm2.pending_batch(_msgs(20)) == []      # puntero restaurado


def test_from_dict_datos_invalidos():
    mm = MemoryManager()
    mm.from_dict(None)
    mm.from_dict({"summaries": "no-lista", "summarized_upto": "x"})
    assert mm.get_summary_text() == ""
