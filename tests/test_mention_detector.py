"""Tests del detector de menciones — recall por nombre conocido, sin regex ciega."""

from narrator.core.mention_detector import detect_mentions

_NOMBRES = ["Kael el Mendigo", "Mira", "El Muelle Viejo"]


def test_menciona_nombre_simple():
    assert detect_mentions("Voy a buscar a Mira en la taberna.", _NOMBRES) == ["Mira"]


def test_menciona_nombre_compuesto_por_ultima_palabra():
    # "Mendigo" alcanza para matchear "Kael el Mendigo" (mismo criterio que VaultWriter)
    assert detect_mentions("Le pregunto al Mendigo sobre el rumor.", _NOMBRES) == ["Kael el Mendigo"]


def test_menciona_nombre_completo():
    assert "Kael el Mendigo" in detect_mentions("Hablo con Kael el Mendigo.", _NOMBRES)


def test_case_insensitive():
    assert detect_mentions("VOY AL MUELLE VIEJO ahora mismo.", _NOMBRES) == ["El Muelle Viejo"]


def test_sin_mencion_devuelve_lista_vacia():
    assert detect_mentions("Reviso mi inventario y descanso.", _NOMBRES) == []


def test_texto_vacio():
    assert detect_mentions("", _NOMBRES) == []
    assert detect_mentions(None, _NOMBRES) == []


def test_sin_nombres_conocidos():
    assert detect_mentions("Cualquier texto", []) == []
    assert detect_mentions("Cualquier texto", None) == []


def test_multiples_menciones_preserva_orden_de_known_names():
    resultado = detect_mentions("Voy a ver a Mira y después al Muelle Viejo.", _NOMBRES)
    assert resultado == ["Mira", "El Muelle Viejo"]


def test_no_duplica_si_matchea_por_dos_criterios():
    # "Kael el Mendigo" completo Y su apellido "Mendigo" aparecen en el texto
    resultado = detect_mentions("Kael el Mendigo, el Mendigo del puerto, me saluda.", _NOMBRES)
    assert resultado.count("Kael el Mendigo") == 1
