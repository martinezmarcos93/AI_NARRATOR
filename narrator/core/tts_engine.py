"""
Motor de TTS local (Fase 22) — narración por voz opcional, 100% offline.

Spike (ver docs/ROADMAP_IMPLEMENTACIONES_2026-07-24.md): se evaluó pyttsx3
sobre SAPI5 (Windows) como candidato — instalación liviana (~9MB:
pyttsx3+pywin32+comtypes), CERO descarga de modelos (usa las voces del
sistema), y esta máquina ya tiene voces en español instaladas de fábrica
(es-ES Helena, es-MX Sabina). Piper/Coqui TTS darían mejor naturalidad
pero requieren descargar modelos de voz (~50-200MB) — quedan como upgrade
futuro si la calidad de SAPI5 no alcanza en la práctica.

engine_factory es inyectable a propósito: permite testear speak_async/stop
sin sintetizar voz real ni depender de pyttsx3 en el proceso de test.
"""

import threading

from narrator.logger import logger


def _default_engine_factory():
    import pyttsx3
    return pyttsx3.init()


class TTSEngine:
    def __init__(self, engine_factory=_default_engine_factory):
        self._engine_factory = engine_factory
        self._engine = None
        self._thread: "threading.Thread | None" = None

    def _get_engine(self):
        if self._engine is None:
            self._engine = self._engine_factory()
        return self._engine

    def is_available(self) -> bool:
        try:
            self._get_engine()
            return True
        except Exception as e:
            logger.error(f"TTS no disponible: {e}", exc_info=True)
            return False

    def speak_async(self, text: str, on_done=None) -> None:
        """Sintetiza y reproduce `text` en un hilo aparte (no bloquea la
        GUI ni el hilo de streaming del LLM). Cancela cualquier
        reproducción en curso antes de empezar una nueva."""
        self.stop()

        def _run():
            try:
                engine = self._get_engine()
                engine.say(text)
                engine.runAndWait()
            except Exception as e:
                logger.error(f"Error en síntesis de voz: {e}", exc_info=True)
            finally:
                if on_done:
                    on_done()

        self._thread = threading.Thread(target=_run, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        """Cancela la reproducción en curso, si hay una."""
        if self._engine is not None:
            try:
                self._engine.stop()
            except Exception as e:
                logger.error(f"Error deteniendo TTS: {e}", exc_info=True)
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=0.5)
