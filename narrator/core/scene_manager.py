"""Sistema de Escenas con condiciones de desbloqueo (C2).

Patrón contenido/estado tomado del Panel de Control de rage_war:
- El CONTENIDO de cada escena vive en el vault (``Escenas/*.md``) con
  frontmatter ``tipo: escena`` — editable en Obsidian.
- El ESTADO (bloqueada → disponible → jugada) se persiste en el
  StateManager (``estado_campana.yaml``).

Frontmatter soportado por escena:
    tipo: escena
    nombre: "Emboscada en el puente"
    detectar: ["puente", "cruzo el río"]   # keywords en el texto del jugador
    requiere_flags: ["mapa_obtenido"]      # flags que deben estar en true
    reloj: "La Horda"                      # se desbloquea si ese reloj se llena
    otorga_flags: ["emboscada_superada"]   # se activan al quedar jugada

Ciclo (100% determinístico, sin LLM):
- bloqueada → disponible: flags requeridos OK y (keyword del jugador,
  o reloj lleno, o sin trigger definido → disponible de entrada).
- disponible → jugada: el narrador la narra (sus keywords aparecen en la
  respuesta del narrador); al jugarse activa sus ``otorga_flags``.
"""

from narrator.logger import logger


def _match(keywords, text: str) -> "str | None":
    """Primera keyword presente en el texto (case-insensitive), o None."""
    if not keywords or not text:
        return None
    t = text.lower()
    for kw in keywords:
        if str(kw).lower() in t:
            return str(kw)
    return None


class SceneManager:
    def __init__(self, retriever, state):
        self.retriever = retriever
        self.state = state

    def _load_scenes(self) -> "list[dict]":
        try:
            return self.retriever.get_by_type("escena", max_files=50)
        except Exception as e:
            logger.error(f"SceneManager: error leyendo escenas del vault: {e}", exc_info=True)
            return []

    # ── Evaluación por turno ──────────────────────────────────
    def evaluate(self, player_text: str = "", narrator_text: str = "") -> dict:
        """Evalúa desbloqueos y escenas jugadas. Devuelve los cambios del turno.

        Las escenas que ya estaban disponibles ANTES de este turno pueden
        pasar a jugadas; las recién desbloqueadas no (evita el salto
        bloqueada→jugada en un mismo turno).
        """
        desbloqueadas: "list[str]" = []
        jugadas: "list[str]" = []
        for scene in self._load_scenes():
            meta = scene.get("meta", {})
            nombre = meta.get("nombre", "")
            if not nombre:
                continue
            estado = self.state.get_scene_state(nombre).get("estado", "bloqueada")

            if estado == "disponible":
                kw = _match(meta.get("detectar"), narrator_text)
                if kw:
                    self.state.set_scene_state(nombre, "jugada")
                    for flag in meta.get("otorga_flags") or []:
                        self.state.set_flag(flag, True,
                                            description=f"otorgado por escena: {nombre}")
                    jugadas.append(nombre)
                continue

            if estado != "bloqueada":
                continue

            requeridos = meta.get("requiere_flags") or []
            if not all(bool(self.state.get_flag(f)) for f in requeridos):
                continue

            detectar = meta.get("detectar") or []
            reloj = meta.get("reloj", "")
            por = ""
            if not detectar and not reloj:
                por = "flags" if requeridos else "inicio"
            elif (kw := _match(detectar, player_text)):
                por = f"keyword: {kw}"
            elif reloj and self.state.is_clock_full(reloj):
                por = f"reloj lleno: {reloj}"
            if por:
                self.state.set_scene_state(nombre, "disponible", por=por)
                desbloqueadas.append(nombre)

        return {"desbloqueadas": desbloqueadas, "jugadas": jugadas}

    # ── Resúmenes ─────────────────────────────────────────────
    def get_prompt_section(self, recien_desbloqueadas: "list[str]" = None) -> str:
        """Sección de escenas para el system prompt del narrador."""
        disponibles = self.state.get_scenes_by_state("disponible")
        if not disponibles and not recien_desbloqueadas:
            return ""
        lines = []
        if recien_desbloqueadas:
            lines.append(
                "DESBLOQUEADAS AHORA (integralas a la narración cuando sea natural, "
                "sin forzar): " + ", ".join(recien_desbloqueadas))
        if disponibles:
            lines.append("Disponibles: " + ", ".join(disponibles))
        return "\n".join(lines)

    def get_status_summary(self) -> str:
        """Resumen para el tab Estado de la GUI."""
        escenas = self.state.data.get("escenas", {})
        if not escenas:
            return ""
        orden = {"disponible": 0, "jugada": 1, "bloqueada": 2}
        marcas = {"disponible": "▶", "jugada": "✓", "bloqueada": "•"}
        lines = []
        for nombre, entry in sorted(escenas.items(),
                                    key=lambda kv: orden.get(kv[1].get("estado", ""), 3)):
            estado = entry.get("estado", "bloqueada")
            lines.append(f"{marcas.get(estado, '•')} {nombre} ({estado})")
        return "\n".join(lines)
