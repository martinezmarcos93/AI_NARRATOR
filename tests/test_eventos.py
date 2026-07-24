"""Test Fase 15: entidad Eventos (timeline causa-efecto) en el vault."""

from narrator.core.vault_writer import VaultWriter


def test_create_event_escribe_frontmatter(tmp_path):
    vw = VaultWriter(vault_path=str(tmp_path / "vault"))
    path = vw.create_event({
        "titulo": "Caída del Puente Viejo",
        "tipo_evento": "historico",
        "causa": "sabotaje de la cofradía rival",
        "efecto": "el puerto quedó aislado",
        "participantes": ["Los Parias"],
    })
    assert path.exists()
    content = path.read_text(encoding="utf-8")
    assert "tipo: evento" in content
    assert "Caída del Puente Viejo" in content
    assert 'tipo_evento: "historico"' in content
    assert "sabotaje" in content


def test_create_event_sin_titulo_devuelve_none(tmp_path):
    vw = VaultWriter(vault_path=str(tmp_path / "vault"))
    assert vw.create_event({"causa": "sin titulo"}) is None


def test_create_event_permite_duplicados_con_sufijo(tmp_path):
    vw = VaultWriter(vault_path=str(tmp_path / "vault"))
    p1 = vw.create_event({"titulo": "Ataque al mercado"})
    p2 = vw.create_event({"titulo": "Ataque al mercado"})
    assert p1 != p2
    assert p1.exists() and p2.exists()


def test_create_event_default_tipo_actual(tmp_path):
    vw = VaultWriter(vault_path=str(tmp_path / "vault"))
    path = vw.create_event({"titulo": "Evento sin tipo"})
    assert 'tipo_evento: "actual"' in path.read_text(encoding="utf-8")
