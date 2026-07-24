"""
Player Agent — IA jugadora que recibe una escena y devuelve una acción,
según un arquetipo de personalidad. Usado por scripts/playtest.py (harness
IA-vs-IA, Fase 20) para testear al narrador de forma automatizada.
"""

ARCHETYPES = {
    "cauteloso": "Sos un jugador CAUTELOSO: evitás riesgos innecesarios, "
                 "investigás antes de actuar, preferís retirarte a arriesgar al grupo.",
    "temerario": "Sos un jugador TEMERARIO: actuás por impulso, buscás el "
                 "conflicto directo, subestimás el peligro.",
    "social": "Sos un jugador SOCIAL: preferís hablar, negociar y persuadir "
              "antes que pelear; te interesan las relaciones entre NPCs.",
    "erudito": "Sos un jugador ERUDITO: investigás el lore, hacés preguntas "
               "sobre el mundo, buscás pistas y patrones antes de actuar.",
    "paranoico": "Sos un jugador PARANOICO: desconfiás de todo NPC, "
                 "sospechás trampas y traiciones, verificás dos veces antes de comprometerte.",
}


class PlayerAgent:
    def __init__(self, llm, archetype: str = "cauteloso"):
        if archetype not in ARCHETYPES:
            raise ValueError(f"Arquetipo desconocido: '{archetype}'. Válidos: {list(ARCHETYPES)}")
        self.llm = llm
        self.archetype = archetype

    def decide_action(self, scene_text: str, character: dict = None) -> str:
        """Devuelve la acción del jugador simulado, en texto libre y
        primera persona, como la escribiría un jugador humano."""
        char_line = f"Tu personaje: {character.get('nombre', '?')}.\n" if character else ""
        prompt = (
            f"{ARCHETYPES[self.archetype]}\n\n{char_line}"
            f"ESCENA:\n{scene_text}\n\n"
            "Respondé en 1-2 oraciones, en primera persona, con la acción "
            "concreta que tu personaje hace ahora. Sin meta-comentarios."
        )
        response = self.llm.chat([{"role": "user", "content": prompt}], max_tokens=100)
        return (response or "").strip()
