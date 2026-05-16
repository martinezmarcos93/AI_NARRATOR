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
