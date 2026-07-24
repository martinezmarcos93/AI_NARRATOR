"""Test Fase 16: deduplicación semántica (por overlap de palabras) de
resúmenes de memoria episódica."""

from narrator.core.memory_manager import MemoryManager, _word_overlap_ratio


class _FakeLLM:
    def __init__(self, respuestas):
        self._respuestas = list(respuestas)

    def chat(self, messages):
        return self._respuestas.pop(0)


def _mensajes(n):
    return [{"role": "user", "content": f"turno {i}"} for i in range(n)]


def test_overlap_identico_es_uno():
    assert _word_overlap_ratio("los PJs entraron a la cripta", "los PJs entraron a la cripta") == 1.0


def test_overlap_textos_distintos_es_bajo():
    assert _word_overlap_ratio("los PJs entraron a la cripta", "el tabernero sirvió cerveza") < 0.3


def test_resumen_parafraseado_se_descarta():
    mm = MemoryManager(working_window=0, batch_size=3, dedup_threshold=0.45)
    llm = _FakeLLM([
        "- Los PJs entraron a la cripta oscura y encontraron un altar antiguo",
        "- El grupo entró a la cripta oscura y halló un altar muy antiguo",
    ])
    mensajes = _mensajes(6)
    assert mm.summarize_batch(mensajes, llm) is True
    assert mm.summarize_batch(mensajes, llm) is False  # parafraseado, se descarta
    assert len(mm._summaries) == 1


def test_resumen_genuinamente_distinto_se_conserva():
    mm = MemoryManager(working_window=0, batch_size=3, dedup_threshold=0.75)
    llm = _FakeLLM([
        "- Los PJs entraron a la cripta oscura",
        "- El tabernero les vendió información sobre el alcalde corrupto",
    ])
    mensajes = _mensajes(6)
    assert mm.summarize_batch(mensajes, llm) is True
    assert mm.summarize_batch(mensajes, llm) is True
    assert len(mm._summaries) == 2


def test_lote_consumido_aunque_sea_duplicado():
    mm = MemoryManager(working_window=0, batch_size=3, dedup_threshold=0.5)
    llm = _FakeLLM(["- hecho A", "- hecho A"])
    mensajes = _mensajes(6)
    mm.summarize_batch(mensajes, llm)
    upto_antes = mm._summarized_upto
    mm.summarize_batch(mensajes, llm)
    assert mm._summarized_upto > upto_antes  # avanzó aunque se descartó el resumen
