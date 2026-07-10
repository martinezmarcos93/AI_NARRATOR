"""Memoria episódica jerárquica (3 capas) para sesiones largas.

Los modelos 7B pierden coherencia cuando el historial completo desborda su
contexto. Este módulo lo evita sin perder memoria:

- Capa 1 (working): los últimos ``working_window`` mensajes van al LLM tal cual.
- Capa 2 (episódica): los turnos que salen de la ventana se resumen en lotes
  a viñetas de hechos clave; los resúmenes acumulados se inyectan al system
  prompt como sección MEMORIA DE LA SESIÓN.
- Capa 3 (larga duración): el RAG semántico sobre el vault (retriever), que
  ya existe fuera de este módulo.
"""

import threading

from narrator.logger import logger

_SUMMARY_PROMPT = """Resumí los siguientes turnos de una partida de rol en 5 a 8 viñetas
concisas y factuales. Registrá SOLO hechos relevantes para la continuidad:
decisiones del jugador, NPCs conocidos, lugares visitados, heridas, objetos
obtenidos o perdidos, promesas y amenazas. Sin florituras narrativas.

=== TURNOS ===
{turns}
"""


class MemoryManager:
    """Mantiene la ventana de trabajo y los resúmenes episódicos de la sesión."""

    def __init__(self, working_window: int = 10, batch_size: int = 10):
        self.working_window = working_window
        self.batch_size = batch_size
        self._summaries: "list[str]" = []
        self._summarized_upto = 0   # índice de messages ya resumidos
        self._lock = threading.Lock()
        self._summarizing = False

    # ── Capa 1: ventana de trabajo ────────────────────────────
    def get_working_messages(self, messages: "list[dict]") -> "list[dict]":
        """Devuelve los mensajes que van al LLM: solo la ventana reciente."""
        if len(messages) <= self.working_window:
            return list(messages)
        return list(messages[-self.working_window:])

    # ── Capa 2: resúmenes episódicos ──────────────────────────
    def get_summary_text(self) -> str:
        with self._lock:
            return "\n".join(self._summaries)

    def pending_batch(self, messages: "list[dict]") -> "list[dict]":
        """Lote de mensajes viejos (fuera de la ventana) aún sin resumir.

        Vacío si todavía no se acumuló un lote completo: se resume de a
        ``batch_size`` para no llamar al LLM en cada turno.
        """
        with self._lock:
            start = self._summarized_upto
        end = len(messages) - self.working_window
        if end - start >= self.batch_size:
            return messages[start:start + self.batch_size]
        return []

    def summarize_batch(self, messages: "list[dict]", llm) -> bool:
        """Resume el próximo lote pendiente (sincrónico; llamar desde un worker).

        Devuelve True si generó un resumen nuevo.
        """
        with self._lock:
            if self._summarizing:
                return False
            self._summarizing = True
        try:
            batch = self.pending_batch(messages)
            if not batch:
                return False
            turns = "\n".join(
                f"[{'Jugador' if m.get('role') == 'user' else 'Narrador'}] {m.get('content', '')}"
                for m in batch
            )
            raw = llm.chat([{"role": "user",
                             "content": _SUMMARY_PROMPT.format(turns=turns[:8000])}])
            if not raw or raw.startswith("[Error"):
                logger.error(f"MemoryManager: resumen fallido: {(raw or '')[:200]}")
                return False
            with self._lock:
                self._summaries.append(raw.strip())
                self._summarized_upto += len(batch)
            return True
        except Exception as e:
            logger.error(f"MemoryManager.summarize_batch: {e}", exc_info=True)
            return False
        finally:
            with self._lock:
                self._summarizing = False

    # ── Ciclo de vida / persistencia ──────────────────────────
    def reset(self) -> None:
        with self._lock:
            self._summaries = []
            self._summarized_upto = 0

    def to_dict(self) -> dict:
        with self._lock:
            return {"summaries": list(self._summaries),
                    "summarized_upto": self._summarized_upto}

    def from_dict(self, data: dict) -> None:
        if not isinstance(data, dict):
            return
        summaries = data.get("summaries", [])
        if not isinstance(summaries, list):
            summaries = []
        try:
            upto = max(0, int(data.get("summarized_upto", 0) or 0))
        except (TypeError, ValueError):
            upto = 0
        with self._lock:
            self._summaries = [s for s in summaries if isinstance(s, str)]
            self._summarized_upto = upto
