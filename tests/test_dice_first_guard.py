"""Tests del detector dice-first — señala, no bloquea."""

from narrator.core.dice_first_guard import check


# 4 casos correctos (no debería marcar sospecha)
def test_con_tirada_no_marca():
    assert check("Ataco al goblin", "Conseguís herirlo con fuerza.", dice_rolled=True) is False


def test_accion_no_checkeable_no_marca():
    assert check("Miro alrededor", "Ves una puerta cerrada.", dice_rolled=False) is False


def test_narracion_sin_resultado_no_marca():
    assert check("Intento persuadirlo", "El guardia te mira fijo.", dice_rolled=False) is False


def test_charla_casual_no_marca():
    assert check("Hola, ¿cómo estás?", "El tabernero sonríe y sirve otra ronda.", dice_rolled=False) is False


# 4 casos incorrectos (debería marcar sospecha)
def test_ataco_sin_tirada_narra_exito():
    assert check("Ataco al orco", "Conseguís herirlo de un golpe certero.", dice_rolled=False) is True


def test_sigilo_sin_tirada_narra_fallo():
    assert check("Intento sigilo para pasar desapercibido", "Fallás y el guardia te ve.", dice_rolled=False) is True


def test_persuado_sin_tirada_narra_resultado():
    assert check("Trato de convencerlo", "Lográs que baje la guardia.", dice_rolled=False) is True


def test_salto_sin_tirada_impacto():
    assert check("Salto al otro techo", "El golpe conecta con el suelo.", dice_rolled=False) is True
