"""
Narrator Agent — procesamiento post-respuesta del narrador.
Detecta tiradas de dados, extracciones de JSON, eventos importantes.
"""

import re
from narrator.logger import logger
import json


class NarratorAgent:
    _DICE_PATTERNS = [
        r"\b\d+[dD]\d+\b",
        r"tirá\s+\d+\s*[dD]\d+",
        r"lanzá\s+\d+\s*dado",
        r"roll\s+\d+[dD]\d+",
    ]

    _EVENT_KEYWORDS = [
        "tirada", "dado", "d20", "d10", "d6", "d8",
        "éxito", "fallo", "fracaso", "consecuencia",
        "herido", "muerto", "muere", "descubrió", "reveló",
        "traición", "acuerdo", "alianza", "emboscada",
    ]

    def extract_dice_request(self, text: str) -> str | None:
        for pat in self._DICE_PATTERNS:
            m = re.search(pat, text, re.IGNORECASE)
            if m:
                return m.group(0)
        return None

    # Sugerencia de tirada con notación explícita (ej. "tirá 5d10", "1D20+3").
    # Solo cuenta/caras — el atributo lo infiere el RuleArbiter por keywords.
    _RE_DICE_SUGGESTION = re.compile(r"\b(\d{1,2})\s*[dD]\s*(\d{1,3})\b")
    _VALID_DICE_SIDES = {4, 6, 8, 10, 12, 20, 100}

    def extract_dice_suggestion(self, text: str) -> "tuple[int, int] | None":
        """Extrae (cantidad, caras) de una sugerencia de tirada del narrador.
        Devuelve None si no hay match o si las caras no son un tipo de dado
        soportado por el panel (D4/D6/D8/D10/D12/D20/D100)."""
        m = self._RE_DICE_SUGGESTION.search(text)
        if not m:
            return None
        n, sides = int(m.group(1)), int(m.group(2))
        if sides not in self._VALID_DICE_SIDES or not (1 <= n <= 20):
            return None
        return n, sides

    def extract_character_json(self, text: str) -> dict | None:
        match = re.search(r"```json\s*(.*?)\s*```", text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(1))
            except (json.JSONDecodeError, ValueError):
                pass
        return None

    def is_important_event(self, text: str) -> bool:
        text_lower = text.lower()
        return any(kw in text_lower for kw in self._EVENT_KEYWORDS)

    def build_log_entry(self, text: str, timestamp: str) -> str:
        first_sentence = re.split(r"[.!?\n]", text.strip())[0]
        return f"[{timestamp}] {first_sentence[:120]}"
