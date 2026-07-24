"""Tests de la bandeja de ideas (Notas/) — creación, transición de estado y promoción."""

import pytest

from narrator.core.ideas_inbox import IdeasInbox


def _inbox(tmp_path) -> IdeasInbox:
    return IdeasInbox(vault_path=str(tmp_path / "vault"))


# ── create ────────────────────────────────────────────────────
def test_create_escribe_frontmatter_correcto(tmp_path):
    inbox = _inbox(tmp_path)
    path = inbox.create("Un culto oculto en los muelles", contenido="Idea suelta.", prioridad="alta")

    assert path.exists()
    content = path.read_text(encoding="utf-8")
    assert "tipo: idea" in content
    assert "estado: raw_idea" in content
    assert "prioridad: alta" in content
    assert "Un culto oculto en los muelles" in content


def test_create_evita_colision_de_nombres(tmp_path):
    inbox = _inbox(tmp_path)
    p1 = inbox.create("Misterio del faro")
    p2 = inbox.create("Misterio del faro")
    assert p1 != p2
    assert p1.exists() and p2.exists()


# ── list_by_state ────────────────────────────────────────────
def test_list_by_state_filtra_correctamente(tmp_path):
    inbox = _inbox(tmp_path)
    inbox.create("Idea A")
    p_b = inbox.create("Idea B")
    inbox.set_state(p_b, "developing")

    raw = inbox.list_by_state("raw_idea")
    dev = inbox.list_by_state("developing")
    assert len(raw) == 1 and raw[0]["meta"]["titulo"] == "Idea A"
    assert len(dev) == 1 and dev[0]["meta"]["titulo"] == "Idea B"


def test_list_by_state_sin_filtro_devuelve_todas(tmp_path):
    inbox = _inbox(tmp_path)
    inbox.create("Idea A")
    inbox.create("Idea B")
    assert len(inbox.list_by_state()) == 2


def test_list_by_state_vault_sin_notas_no_rompe(tmp_path):
    inbox = _inbox(tmp_path)
    assert inbox.list_by_state() == []


# ── set_state ────────────────────────────────────────────────
def test_set_state_actualiza_frontmatter(tmp_path):
    inbox = _inbox(tmp_path)
    path = inbox.create("Idea C")
    assert inbox.set_state(path, "ready_to_implement") is True

    ideas = inbox.list_by_state("ready_to_implement")
    assert len(ideas) == 1
    assert ideas[0]["meta"]["estado"] == "ready_to_implement"


def test_set_state_invalido_lanza_error(tmp_path):
    inbox = _inbox(tmp_path)
    path = inbox.create("Idea D")
    with pytest.raises(ValueError):
        inbox.set_state(path, "estado_inventado")


def test_set_state_archivo_inexistente_devuelve_false(tmp_path):
    inbox = _inbox(tmp_path)
    assert inbox.set_state(tmp_path / "no_existe.md", "developing") is False


# ── promote ──────────────────────────────────────────────────
def test_promote_a_npc_crea_archivo_formal_y_marca_implementada(tmp_path):
    inbox = _inbox(tmp_path)
    idea_path = inbox.create("Kael el Mendigo", contenido="Un NPC misterioso.")

    npc_path = inbox.promote(idea_path, tipo="npc")

    assert npc_path.exists()
    assert npc_path.parent.name == "NPCs"
    npc_content = npc_path.read_text(encoding="utf-8")
    assert "tipo: npc" in npc_content
    assert "Kael el Mendigo" in npc_content
    assert "Un NPC misterioso." in npc_content

    # La idea original queda marcada como implementada
    idea_content = idea_path.read_text(encoding="utf-8")
    assert "estado: implemented" in idea_content


def test_promote_a_locacion(tmp_path):
    inbox = _inbox(tmp_path)
    idea_path = inbox.create("El Muelle Viejo")
    loc_path = inbox.promote(idea_path, tipo="locacion")
    assert loc_path.parent.name == "Locaciones"
    assert "tipo: locacion" in loc_path.read_text(encoding="utf-8")


def test_promote_tipo_no_soportado_lanza_error(tmp_path):
    inbox = _inbox(tmp_path)
    idea_path = inbox.create("Idea E")
    with pytest.raises(ValueError):
        inbox.promote(idea_path, tipo="frente")
