"""
Narrator Agent — procesamiento post-respuesta del narrador.
Detecta tiradas de dados, extracciones de JSON, eventos importantes.
"""

import re
import json


class NarratorAgent:
    # Patrones de tirada de dados
    _DICE_PATTERNS = [
        r"\b\d+[dD]\d+\b",            # "2d6", "1D20"
        r"tirá\s+\d+\s*[dD]\d+",      # "tirá 2D10"
        r"lanzá\s+\d+\s*dado",         # "lanzá 3 dados"
        r"roll\s+\d+[dD]\d+",          # inglés
    ]

    # Palabras clave que indican evento narrativo importante
    _EVENT_KEYWORDS = [
        "tirada", "dado", "d20", "d10", "d6", "d8",
        "éxito", "fallo", "fracaso", "consecuencia",
        "herido", "muerto", "muere", "descubrió", "reveló",
        "traición", "acuerdo", "alianza", "emboscada",
    ]

    def extract_dice_request(self, text: str) -> str | None:
        """
        Si el narrador está pidiendo una tirada, devuelve la descripción.
        Retorna None si no hay tirada.
        """
        for pat in self._DICE_PATTERNS:
            m = re.search(pat, text, re.IGNORECASE)
            if m:
                return m.group(0)
        return None

    def extract_character_json(self, text: str) -> dict | None:
        """
        Extrae el bloque ```json ... ``` del texto de respuesta del narrador.
        El narrador lo emite cuando actualiza la hoja de personaje.
        """
        match = re.search(r"```json\s*(.*?)\s*```", text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(1))
            except (json.JSONDecodeError, ValueError):
                pass
        return None

    def is_important_event(self, text: str) -> bool:
        """True si la respuesta contiene un evento narrativo clave que vale la pena loguear."""
        text_lower = text.lower()
        return any(kw in text_lower for kw in self._EVENT_KEYWORDS)

    def build_log_entry(self, text: str, timestamp: str) -> str:
        """Genera una entrada compacta para el log de sesión."""
        # Tomar las primeras 120 chars de la primera oración
        first_sentence = re.split(r"[.!?\n]", text.strip())[0]
        return f"[{timestamp}] {first_sentence[:120]}"
