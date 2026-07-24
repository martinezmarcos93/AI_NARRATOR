"""Tests del motor de TTS (Fase 22) — con motor falso, sin sintetizar audio real."""

import threading

from narrator.core.tts_engine import TTSEngine


class _FakeEngine:
    def __init__(self):
        self.said = []
        self.stopped = False
        self.ran = False

    def say(self, text):
        self.said.append(text)

    def runAndWait(self):
        self.ran = True

    def stop(self):
        self.stopped = True


def test_is_available_con_factory_ok():
    tts = TTSEngine(engine_factory=_FakeEngine)
    assert tts.is_available() is True


def test_is_available_con_factory_rota():
    def factory():
        raise RuntimeError("sin motor de voz instalado")

    tts = TTSEngine(engine_factory=factory)
    assert tts.is_available() is False


def test_speak_async_no_bloquea_y_llama_say_run_and_wait():
    fake = _FakeEngine()
    tts = TTSEngine(engine_factory=lambda: fake)
    done = threading.Event()

    tts.speak_async("hola narrador", on_done=done.set)

    assert done.wait(timeout=2), "speak_async no debe bloquear ni colgarse"
    assert fake.said == ["hola narrador"]
    assert fake.ran is True


def test_speak_async_cancela_reproduccion_previa():
    fake = _FakeEngine()
    tts = TTSEngine(engine_factory=lambda: fake)
    done1 = threading.Event()
    done2 = threading.Event()

    tts.speak_async("primero", on_done=done1.set)
    done1.wait(timeout=2)
    tts.speak_async("segundo", on_done=done2.set)
    assert done2.wait(timeout=2)
    assert "segundo" in fake.said


def test_stop_sin_engine_inicializado_no_rompe():
    tts = TTSEngine(engine_factory=_FakeEngine)
    tts.stop()  # no debe lanzar aunque nunca se haya usado speak_async


def test_stop_detiene_el_motor():
    fake = _FakeEngine()
    tts = TTSEngine(engine_factory=lambda: fake)
    tts._engine = fake  # simula motor ya inicializado
    tts.stop()
    assert fake.stopped is True
