"""
Prompt Builder — construye prompts de sistema desde configuración YAML + contexto del vault.
Mantiene el contexto total dentro de un budget de palabras para modelos pequeños.
"""

import json
import yaml
from pathlib import Path


NARRATIVE_PRINCIPLES = """PRINCIPIOS NARRATIVOS:
- La historia EMERGE de las decisiones del jugador. Nunca está pre-escrita.
- Cada escena tiene tensión: física, emocional, moral, psicológica o existencial.
- Los fallos SIEMPRE avanzan la historia con complicaciones. Nunca bloquean.
- El mundo recuerda: las consecuencias persisten entre sesiones.
- Mostrar, nunca explicar. ("Los guardias dejan de sonreír cuando pasa el carruaje.")
- Dosificar información: el misterio parcial es más poderoso que la revelación total.
- Si se pide tirada de dados: indicá qué habilidad aplica y qué dados lanzar."""

DICE_RESOLUTION_RULES = """RESOLUCIÓN DE TIRADAS:
- Éxito total: la acción sale, narrá con riqueza cinématica.
- Éxito parcial (PbtA 7-9): ofrecé una elección difícil.
- Fallo: complicación interesante, la historia avanza igual."""


class PromptBuilder:
    def __init__(self, systems_path: str = "./systems"):
        self.systems_path = Path(systems_path)
        self._cache: dict[str, dict] = {}

    # ── Sistema ───────────────────────────────────────────────
    def load_system(self, slug: str) -> dict:
        if slug in self._cache:
            return self._cache[slug]
        path = self.systems_path / f"{slug}.yaml"
        if not path.exists():
            path = self.systems_path / "generic.yaml"
        with open(path, encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        self._cache[slug] = data
        return data

    def detect_system_from_text(self, text: str) -> str:
        """Auto-detecta el sistema desde texto de PDF/manual."""
        t = text.lower()
        if any(w in t for w in ["vampiro", "mascarada", "brujah", "camarilla", "malkavian", "sabbat", "toreador", "nosferatu"]):
            return "vtm_v20"
        if any(w in t for w in ["hombre lobo", "garou", "apocalipsis", "tribus garou", "werewolf"]):
            return "vtm_v20"  # WtA usa base VtM por ahora
        if any(w in t for w in ["pathfinder", "golarion", "paizo", "starfinder", "absalom"]):
            return "pathfinder_2e"
        if any(w in t for w in ["dungeon", "dungeons & dragons", "d&d", "cleric", "paladin", "warlock", "tiefling", "druid"]):
            return "dnd_5e"
        if any(w in t for w in ["call of cthulhu", "investigador", "cordura", "mythos", "cthulhu", "keeper", "lovecraft"]):
            return "coc_7e"
        if any(w in t for w in ["apocalypse world", "pbta", "powered by the apocalypse", "maestro de ceremonias", "movimientos"]):
            return "generic"
        return "generic"

    # ── Prompt principal del narrador ─────────────────────────
    def build_narrator_prompt(
        self,
        system_slug: str,
        vault_context: str = "",
        character: dict = None,
        last_session: str = "",
        scene_location: str = "",
        active_npcs: str = "",
        active_fronts: str = "",
        clocks_summary: str = "",
    ) -> str:
        sys = self.load_system(system_slug)
        base_prompt = sys.get("llm_system_prompt", "Eres un narrador de juego de rol.")
        voc = sys.get("vocabulario", {})

        sections = [base_prompt, NARRATIVE_PRINCIPLES, DICE_RESOLUTION_RULES]

        if voc:
            voc_lines = []
            if voc.get("grupo_pc"):
                voc_lines.append(f"- Grupo de personajes: '{voc['grupo_pc']}'")
            if voc.get("eje_horror"):
                voc_lines.append(f"- Eje dramático: {voc['eje_horror']}")
            if voc.get("mecanica_moral"):
                voc_lines.append(f"- Mecánica moral: {voc['mecanica_moral']}")
            if voc_lines:
                sections.append("VOCABULARIO DEL SISTEMA:\n" + "\n".join(voc_lines))

        if scene_location:
            sections.append(f"LOCACIÓN ACTUAL: {scene_location}")

        if last_session:
            sections.append(f"ÚLTIMA SESIÓN:\n{last_session}")

        if clocks_summary:
            sections.append(f"RELOJES DE FRENTES:\n{clocks_summary}")

        if active_fronts:
            sections.append(f"FRENTES ACTIVOS:\n{active_fronts}")

        if active_npcs:
            sections.append(f"NPCS EN EL MUNDO:\n{active_npcs}")

        if vault_context:
            sections.append(f"CONTEXTO RELEVANTE DEL VAULT:\n{vault_context}")

        if character:
            char_str = json.dumps(character, ensure_ascii=False, indent=2)
            sections.append(f"HOJA DEL PERSONAJE JUGADOR:\n{char_str}")

        return "\n\n".join(sections)

    # ── Prompt de creación de personaje ──────────────────────
    def build_char_creation_prompt(
        self,
        system_slug: str,
        manual_excerpt: str = "",
    ) -> str:
        sys = self.load_system(system_slug)
        base_prompt = sys.get("llm_system_prompt", "Eres un narrador de juego de rol.")
        voc = sys.get("vocabulario", {})
        campos = sys.get("npc_campos_extra", [])

        campos_labels = [c.get("label", "") for c in campos if c.get("label")]
        campos_str = ", ".join(campos_labels) if campos_labels else "nombre, historia, habilidades"

        sections = [
            base_prompt,
            "MODO ACTIVO: Creación de Personaje",
            f"Tu tarea es guiar al jugador para crear un {voc.get('personaje_term', 'personaje')} paso a paso.",
            "Instrucciones:",
            "- Presentá opciones numeradas con sabor narrativo, no solo mecánico.",
            "- Preguntá de a UNA sección por vez. No abrumés con demasiadas preguntas.",
            f"- Campos importantes para completar: {campos_str}.",
            "- Cuando tengas datos concretos, incluilos en un bloque ```json``` al final de tu respuesta.",
            "- Adaptá el tono al sistema y al personaje que está emergiendo.",
        ]

        if manual_excerpt:
            sections.append(f"EXTRACTO DEL MANUAL (referencia):\n{manual_excerpt[:2000]}")

        return "\n\n".join(sections)

    # ── Prompt de decisión de NPC ─────────────────────────────
    def build_npc_action_prompt(
        self,
        system_slug: str,
        npc_data: dict,
        world_state: str,
    ) -> str:
        sys = self.load_system(system_slug)
        action_pool = sys.get("npc_acciones", [
            "observar y esperar",
            "reunirse con aliados",
            "avanzar agenda propia",
            "recolectar información",
        ])
        acciones_str = "\n".join(f"  {i+1}. {a}" for i, a in enumerate(action_pool))

        npc_name = npc_data.get("nombre", "NPC desconocido")
        npc_agenda = npc_data.get("agenda", npc_data.get("rol", "agenda desconocida"))
        npc_faction = npc_data.get("clan", npc_data.get("faccion", npc_data.get("afiliacion", "")))

        return (
            f"Simulador de comportamiento de personaje.\n\n"
            f"NPC: {npc_name}"
            + (f" ({npc_faction})" if npc_faction else "")
            + f"\nAgenda: {npc_agenda}\n"
            f"Estado del mundo: {world_state}\n\n"
            f"Elegí UNA acción de la lista y explicá brevemente cómo la ejecuta este NPC:\n"
            f"{acciones_str}\n\n"
            f"Respondé EXACTAMENTE con este formato:\n"
            f"ACCIÓN: [nombre de la acción] | DESCRIPCIÓN: [cómo la ejecuta, máximo 25 palabras]"
        )
