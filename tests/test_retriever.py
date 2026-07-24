"""Tests de VaultRetriever — lorebook (Fase 5) y metadata de token (Fase 8)."""

from pathlib import Path

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


# ── get_active_npcs_summary: metadata de token (Fase 8) ──────────
def _write_npc(vault: "Path", filename: str, frontmatter_lines: "list[str]"):
    npcs_dir = vault / "NPCs"
    npcs_dir.mkdir(parents=True, exist_ok=True)
    content = "---\n" + "\n".join(frontmatter_lines) + "\n---\n\nCuerpo del NPC.\n"
    (npcs_dir / filename).write_text(content, encoding="utf-8")


def test_summary_incluye_icono_y_amenaza(tmp_path):
    vault = tmp_path / "vault_npcs"
    _write_npc(vault, "Kael.md", [
        "tipo: npc", 'nombre: "Kael"', 'clan: "Nosferatu"',
        "amenaza: alta", 'icono: "🔴"', 'estado: "vivo"', "condiciones: []",
    ])
    r = VaultRetriever(vault_path=str(vault))
    summary = r.get_active_npcs_summary()
    assert "🔴 Kael" in summary
    assert "[amenaza:alta]" in summary
    assert "[VIVO]" not in summary  # estado por defecto no se muestra


def test_summary_marca_estado_no_vivo(tmp_path):
    vault = tmp_path / "vault_npcs"
    _write_npc(vault, "Goblin.md", [
        "tipo: npc", 'nombre: "Goblin"', 'estado: "muerto"',
    ])
    r = VaultRetriever(vault_path=str(vault))
    summary = r.get_active_npcs_summary()
    assert "[MUERTO]" in summary


def test_summary_incluye_condiciones(tmp_path):
    vault = tmp_path / "vault_npcs"
    _write_npc(vault, "Mira.md", [
        "tipo: npc", 'nombre: "Mira"',
        "condiciones:", "  - envenenada", "  - aturdida",
    ])
    r = VaultRetriever(vault_path=str(vault))
    summary = r.get_active_npcs_summary()
    assert "condiciones: envenenada, aturdida" in summary
