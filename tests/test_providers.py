"""Tests de la factory de proveedores de LLM (Ollama first-class, sin credenciales)."""

import pytest

from narrator.core.providers import OllamaProvider, create_provider


# ── create_provider: defaults sin config ────────────────────────
def test_sin_config_usa_ollama_localhost():
    provider = create_provider()
    assert isinstance(provider, OllamaProvider)
    assert provider._client.base_url == "http://localhost:11434"
    assert provider._client.model == "llama3.2"


def test_config_vacia_usa_defaults():
    provider = create_provider(config={})
    assert isinstance(provider, OllamaProvider)
    assert provider._client.base_url == "http://localhost:11434"


# ── config.yaml real del proyecto: comportamiento idéntico al actual ──
def test_config_actual_del_proyecto_no_cambia_comportamiento():
    config = {
        "llm": {
            "backend": "ollama",
            "model": "mistral:7b",
            "base_url": "http://localhost:11434",
        }
    }
    provider = create_provider(config)
    assert provider._client.base_url == "http://localhost:11434"
    assert provider._client.model == "mistral:7b"


# ── override explícito de modelo (como state["model"] en app.py) ──
def test_model_param_tiene_prioridad_sobre_config():
    config = {"llm": {"model": "mistral:7b"}}
    provider = create_provider(config, model="llama3.1:8b")
    assert provider._client.model == "llama3.1:8b"


# ── base_url custom (ej. Ollama en otra máquina de la red local) ──
def test_base_url_custom():
    config = {"llm": {"backend": "ollama", "base_url": "http://192.168.1.50:11434"}}
    provider = create_provider(config)
    assert provider._client.base_url == "http://192.168.1.50:11434"


# ── backend desconocido: no se inventa soporte ──────────────────
def test_backend_desconocido_lanza_error_claro():
    with pytest.raises(ValueError, match="lmstudio"):
        create_provider({"llm": {"backend": "lmstudio"}})


# ── interfaz AIProvider: delega correctamente a LLMClient ───────
class _FakeLLMClient:
    def __init__(self, base_url=None, model=None):
        self.base_url = base_url
        self.model = model
        self.chat_calls = []

    def chat(self, messages, max_tokens=300):
        self.chat_calls.append((messages, max_tokens))
        return "respuesta simulada"

    def stream_chat(self, messages, on_chunk, on_done, max_tokens=600):
        on_chunk("hola")
        on_done("hola")

    def is_connected(self):
        return True

    def get_models(self):
        return ["llama3.2"]


def test_ollama_provider_delega_chat(monkeypatch):
    import narrator.core.providers as providers_mod

    monkeypatch.setattr(providers_mod, "LLMClient", _FakeLLMClient)
    provider = providers_mod.OllamaProvider(base_url="http://x", model="m")
    assert provider.chat([{"role": "user", "content": "hola"}]) == "respuesta simulada"
    assert provider.is_available() is True
    assert provider.get_models() == ["llama3.2"]


def test_ollama_provider_delega_stream_chat(monkeypatch):
    import narrator.core.providers as providers_mod

    monkeypatch.setattr(providers_mod, "LLMClient", _FakeLLMClient)
    provider = providers_mod.OllamaProvider(base_url="http://x", model="m")
    chunks = []
    done = []
    provider.stream_chat([], on_chunk=chunks.append, on_done=done.append)
    assert chunks == ["hola"]
    assert done == ["hola"]
