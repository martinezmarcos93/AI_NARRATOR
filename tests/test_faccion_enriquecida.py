"""Test Fase 14: modelo de organización/facción más rico (metas/recursos/
influencia/relaciones), y que el prompt de extracción siga siendo válido."""

from narrator.agents.extractor_agent import _EXTRACT_FACTIONS_PROMPT, _faction_frontmatter


def test_prompt_formatea_sin_romper_por_las_llaves_nuevas():
    p = _EXTRACT_FACTIONS_PROMPT.format(text="texto de prueba")
    assert "texto de prueba" in p
    assert "relaciones" in p


def test_faccion_frontmatter_incluye_campos_ricos():
    fm = _faction_frontmatter({
        "nombre": "Los Parias",
        "agenda": "controlar el puerto",
        "recursos": ["contactos", "armas"],
        "influencia": "media",
        "relaciones": [{"faccion": "La Corte", "tipo": "enemiga"}],
    })
    assert 'metas: "controlar el puerto"' in fm
    assert 'recursos: ["contactos", "armas"]' in fm
    assert 'influencia: "media"' in fm
    assert '"faccion": "La Corte"' in fm


def test_faccion_frontmatter_sin_campos_ricos_no_rompe():
    fm = _faction_frontmatter({"nombre": "Facción Simple"})
    assert "tipo: cofradia" in fm
    assert "Facción Simple" in fm
