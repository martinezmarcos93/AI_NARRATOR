"""Tests del lorebook por keywords — RAG liviano sin embeddings."""

from narrator.core.lorebook import get_matching_content, match_entries

_ENTRIES = [
    {"keywords": ["vaulderie", "lazo de sangre"], "content": "Vaulderie: ritual de sangre.", "priority": 5},
    {"keywords": ["frenesí", "bestia"], "content": "Frenesí: pérdida de control.", "priority": 5},
    {"keywords": ["mascarada"], "content": "Mascarada: secreto vampírico.", "priority": 4},
]


# ── match_entries ────────────────────────────────────────────────
def test_match_por_keyword_presente():
    matched = match_entries(_ENTRIES, "El vampiro invoca la Vaulderie ante su manada.")
    assert len(matched) == 1
    assert matched[0]["content"] == "Vaulderie: ritual de sangre."


def test_match_case_insensitive():
    matched = match_entries(_ENTRIES, "ROMPIÓ LA MASCARADA frente a testigos.")
    assert len(matched) == 1
    assert "Mascarada" in matched[0]["content"]


def test_match_multiple_entradas():
    matched = match_entries(_ENTRIES, "Entra en frenesí como una bestia salvaje.")
    assert len(matched) == 1  # ambas keywords ("frenesí","bestia") son de la MISMA entrada


def test_sin_match_devuelve_lista_vacia():
    assert match_entries(_ENTRIES, "Charla tranquila en la taberna.") == []


def test_texto_vacio_devuelve_lista_vacia():
    assert match_entries(_ENTRIES, "") == []
    assert match_entries(_ENTRIES, None) == []


def test_entradas_vacias_no_rompe():
    assert match_entries([], "cualquier texto") == []
    assert match_entries(None, "cualquier texto") == []


# ── get_matching_content: orden por prioridad + budget de palabras ──
def test_orden_por_prioridad_descendente():
    entries = [
        {"keywords": ["x"], "content": "baja prioridad", "priority": 1},
        {"keywords": ["x"], "content": "alta prioridad", "priority": 9},
    ]
    result = get_matching_content(entries, "x")
    assert result.index("alta prioridad") < result.index("baja prioridad")


def test_respeta_presupuesto_de_palabras():
    entries = [
        {"keywords": ["x"], "content": "una dos tres cuatro cinco", "priority": 5},
        {"keywords": ["x"], "content": "seis siete", "priority": 1},
    ]
    result = get_matching_content(entries, "x", max_words=5)
    assert "una dos tres cuatro cinco" in result
    assert "seis siete" not in result


def test_entrada_corta_entra_aunque_una_mas_prioritaria_no_quepa():
    entries = [
        {"keywords": ["x"], "content": "una dos tres cuatro cinco seis siete ocho", "priority": 9},
        {"keywords": ["x"], "content": "corta", "priority": 1},
    ]
    result = get_matching_content(entries, "x", max_words=3)
    assert result == "corta"


def test_sin_match_devuelve_cadena_vacia():
    assert get_matching_content(_ENTRIES, "nada relacionado acá") == ""
