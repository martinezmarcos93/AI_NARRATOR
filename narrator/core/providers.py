"""
Factory de proveedores de LLM — Ollama local por defecto, sin credenciales.

No reemplaza LLMClient (sigue siendo el wrapper real de Ollama, usado
directamente en toda la app). Esto es la capa de selección: lee
`config.yaml` y decide qué proveedor instanciar, dejando la puerta abierta
a otros backends compatibles a futuro sin romper el modo 100% local actual.
"""

from abc import ABC, abstractmethod
from typing import Callable

from narrator.core.llm_client import LLMClient

# Presets conocidos: base_url por defecto de cada backend soportado.
PRESETS: dict[str, dict] = {
    "ollama": {"base_url": "http://localhost:11434"},
}

_DEFAULT_BACKEND = "ollama"
_DEFAULT_MODEL = "llama3.2"


class AIProvider(ABC):
    """Interfaz mínima que cualquier backend de LLM debe cumplir."""

    @abstractmethod
    def chat(self, messages: list[dict], max_tokens: int = 300) -> str:
        ...

    @abstractmethod
    def stream_chat(
        self,
        messages: list[dict],
        on_chunk: Callable[[str], None],
        on_done: Callable[[str], None],
        max_tokens: int = 600,
    ) -> None:
        ...

    @abstractmethod
    def is_available(self) -> bool:
        ...


class OllamaProvider(AIProvider):
    """Adapta LLMClient (wrapper real de Ollama) a la interfaz AIProvider."""

    def __init__(self, base_url: str, model: str):
        self._client = LLMClient(base_url=base_url, model=model)

    def chat(self, messages: list[dict], max_tokens: int = 300) -> str:
        return self._client.chat(messages, max_tokens=max_tokens)

    def stream_chat(self, messages, on_chunk, on_done, max_tokens: int = 600) -> None:
        self._client.stream_chat(messages, on_chunk, on_done, max_tokens=max_tokens)

    def is_available(self) -> bool:
        return self._client.is_connected()

    def get_models(self) -> list[str]:
        return self._client.get_models()


def create_provider(config: dict = None, model: str = None) -> AIProvider:
    """Instancia el AIProvider indicado en `config["llm"]`.

    Sin `config` o sin la clave `llm`, usa el preset "ollama" con el
    comportamiento idéntico al hardcodeado hoy (localhost:11434). El
    `backend` declarado debe estar en PRESETS — no se inventa soporte
    para backends no implementados.
    """
    llm_cfg = (config or {}).get("llm", {}) or {}
    backend = llm_cfg.get("backend", _DEFAULT_BACKEND)

    if backend not in PRESETS:
        raise ValueError(
            f"Backend de LLM desconocido: '{backend}'. Soportados: {list(PRESETS)}"
        )

    base_url = llm_cfg.get("base_url") or PRESETS[backend]["base_url"]
    resolved_model = model or llm_cfg.get("model", _DEFAULT_MODEL)

    if backend == "ollama":
        return OllamaProvider(base_url=base_url, model=resolved_model)
    raise ValueError(f"Backend '{backend}' registrado en PRESETS pero sin implementación.")
