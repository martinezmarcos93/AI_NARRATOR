"""Tests de la psicología de NPCs (arquetipos + rasgos → línea de prompt)."""

from narrator.agents.extractor_agent import _npc_frontmatter
from narrator.core.npc_psyche import format_psyche_line, validate_psyche


# ── Validación ────────────────────────────────────────────────
def test_validate_arquetipo_valido():
    arq, _ = validate_psyche("Sombra", {})
    assert arq == "sombra"


def test_validate_arquetipo_invalido():
    arq, _ = validate_psyche("dragón", {})
    assert arq == ""
    assert validate_psyche(None, None) == ("", {})


def test_validate_rasgos_clamp_y_filtro():
    _, rasgos = validate_psyche("", {"agresividad": 1.7, "empatia": -0.3,
                                     "inventado": 0.5, "extraversion": "x"})
    assert rasgos == {"agresividad": 1.0, "empatia": 0.0}


# ── Línea para el prompt ──────────────────────────────────────
def test_format_linea_completa():
    meta = {"arquetipo": "sombra",
            "rasgos": {"agresividad": 0.8, "empatia": 0.2, "amabilidad": 0.5}}
    line = format_psyche_line(meta)
    assert line.startswith("psique: sombra (")
    assert "agresividad alta" in line
    assert "empatia baja" in line
    assert "amabilidad" not in line          # rasgo neutral no satura el prompt


def test_format_sin_datos():
    assert format_psyche_line({}) == ""
    assert format_psyche_line({"nombre": "Orsik"}) == ""
    assert format_psyche_line(None) == ""


def test_format_solo_rasgos():
    line = format_psyche_line({"rasgos": {"neuroticismo": 0.9}})
    assert line == "psique: neuroticismo alta"


# ── Frontmatter del extractor ─────────────────────────────────
def test_frontmatter_incluye_psique():
    data = {"nombre": "Vesna", "rol": "informante", "arquetipo": "trickster",
            "rasgos": {"impulsividad": 0.7, "empatia": 0.3}}
    fm = _npc_frontmatter(data, "vtm_v20")
    assert 'arquetipo: "trickster"' in fm
    assert "rasgos:" in fm
    assert "  impulsividad: 0.7" in fm


def test_frontmatter_psique_invalida_se_omite():
    data = {"nombre": "Orsik", "arquetipo": "tabernero", "rasgos": "no-dict"}
    fm = _npc_frontmatter(data, "generic")
    assert "arquetipo" not in fm
    assert "rasgos" not in fm


def test_frontmatter_roundtrip_yaml():
    import frontmatter as fmlib
    data = {"nombre": "Vesna", "arquetipo": "sombra",
            "rasgos": {"agresividad": 0.8}}
    text = _npc_frontmatter(data, "vtm_v20") + "\n\ncuerpo"
    post = fmlib.loads(text)
    assert post.metadata["arquetipo"] == "sombra"
    assert post.metadata["rasgos"]["agresividad"] == 0.8
    # La línea de prompt sale directo del frontmatter parseado
    assert "psique: sombra" in format_psyche_line(post.metadata)
