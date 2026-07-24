"""
Detector "dice-first" — heurística estructural para el principio "el
RuleArbiter resuelve, el LLM narra": detecta cuándo la acción del jugador
sonaba a algo que requería tirada y el narrador ya narró un resultado
(éxito/fallo) SIN que se haya tirado en el turno. No bloquea el flujo,
solo señala (log/aviso) — el veredicto real sigue siendo del RuleArbiter.
"""

_VERBOS_INCERTIDUMBRE = [
    "intento", "trato de", "ataco", "golpeo", "disparo", "esquivo",
    "persuado", "convenzo", "engaño", "sigilo", "me escondo", "trepo",
    "salto", "investigo", "busco", "resisto", "aguanto", "seduzco",
    "intimido", "robo", "hackeo", "descifro",
]

_LENGUAJE_RESULTADO = [
    "consegu", "logr", "fall", "el golpe conecta", "la tirada",
    "acertás", "acertas", "errás", "erras", "impact",
    "sale bien", "sale mal", "tenés éxito", "tenes exito", "fracas",
]


def player_action_sounds_checkable(player_text: str) -> bool:
    """¿La acción del jugador suena a algo que requeriría una tirada?"""
    t = (player_text or "").lower()
    return any(v in t for v in _VERBOS_INCERTIDUMBRE)


def narration_states_result(narrator_text: str) -> bool:
    """¿La narración del Máster ya afirma un resultado (éxito/fallo)?"""
    t = (narrator_text or "").lower()
    return any(v in t for v in _LENGUAJE_RESULTADO)


def check(player_text: str, narrator_text: str, dice_rolled: bool) -> bool:
    """True si hay una violación "dice-first" sospechada: la acción sonaba
    a tirada, el narrador ya narra un resultado, pero no se tiró este turno."""
    if dice_rolled:
        return False
    return player_action_sounds_checkable(player_text) and narration_states_result(narrator_text)
