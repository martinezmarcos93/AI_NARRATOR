"""Tests de VaultRetriever — foco en la integración de lorebook (Fase 5)."""

from narrator.core.retriever import VaultRetriever

_LOREBOOK = [
    {"keywords": ["vaulderie"], "content": "La Vaulderie crea un lazo de sangre.", "priority": 5},
]


def _retriever(tmp_path) -> VaultRetriever:
    # Vault vacío: alcanza para aislar el comportamiento del lorebook,
    # no requiere archivos .md reales.
    return VaultRetriever(vault_path=str(tmp_path / "vault_vacio"))


def test_lorebook_se_agrega_sin_embeddings_disponibles(tmp_path):
    r = _retriever(tmp_path)
    r._embedder._available = False  # simula que nomic-embed-text no está instalado

    ctx = r.get_relevant_context("Invoco la Vaulderie con mi manada", lorebook_entries=_LOREBOOK)
    assert "Vaulderie crea un lazo de sangre" in ctx


def test_lorebook_no_se_agrega_con_embeddings_disponibles(tmp_path):
    r = _retriever(tmp_path)
    r._embedder._available = True  # simula que la búsqueda semántica sí está disponible

    ctx = r.get_relevant_context("Invoco la Vaulderie con mi manada", lorebook_entries=_LOREBOOK)
    assert "Vaulderie crea un lazo de sangre" not in ctx


def test_sin_lorebook_entries_no_rompe(tmp_path):
    r = _retriever(tmp_path)
    r._embedder._available = False
    assert r.get_relevant_context("cualquier cosa", lorebook_entries=None) == ""


def test_lorebook_sin_match_no_agrega_nada(tmp_path):
    r = _retriever(tmp_path)
    r._embedder._available = False
    ctx = r.get_relevant_context("charla casual sin temas de reglas", lorebook_entries=_LOREBOOK)
    assert ctx == ""
