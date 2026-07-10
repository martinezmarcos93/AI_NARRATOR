"""Psicología de NPCs: arquetipos jungianos + rasgos dimensionales.

Patrón tomado de PSYCHE SIMULACRA reducido a lo útil para el narrador:
cada NPC lleva en su frontmatter un ``arquetipo`` dominante (12 jungianos)
y un dict ``rasgos`` (0.0–1.0). Este módulo valida esos datos y los
convierte en UNA línea conductual que se inyecta al prompt para que los
diálogos y decisiones del NPC tengan una personalidad consistente.
"""

ARQUETIPOS = (
    "self", "persona", "sombra", "anima_animus",
    "heroe", "sabio", "trickster", "madre",
    "padre", "nino_divino", "gobernante", "rebelde",
)

# Guía de conducta por arquetipo dominante (va al prompt del narrador)
_CONDUCTA = {
    "self":         "equilibrado; busca integrar posturas y mediar",
    "persona":      "cuida su imagen pública; dice lo socialmente correcto",
    "sombra":       "guarda secretos e impulsos ocultos; desconfiado",
    "anima_animus": "emocional e intuitivo; se guía por los vínculos",
    "heroe":        "frontal y protector; asume riesgos por otros",
    "sabio":        "analítico y distante; habla poco y con precisión",
    "trickster":    "engañoso y burlón; miente con encanto, cambia de bando",
    "madre":        "cálido y protector; prioriza el cuidado de los suyos",
    "padre":        "autoritario y estructurado; exige respeto",
    "nino_divino":  "ingenuo y curioso; despierta instinto de protección",
    "gobernante":   "controlador; negocia siempre desde el poder",
    "rebelde":      "desafía la autoridad; imprevisible",
}

RASGOS = ("extraversion", "amabilidad", "neuroticismo",
          "impulsividad", "agresividad", "empatia")

_UMBRAL_ALTO = 0.65
_UMBRAL_BAJO = 0.35


def validate_psyche(arquetipo, rasgos) -> "tuple[str, dict]":
    """Sanitiza datos de psique venidos del LLM/vault. Nunca lanza."""
    arq = str(arquetipo or "").strip().lower().replace(" ", "_")
    if arq not in ARQUETIPOS:
        arq = ""
    clean: dict = {}
    if isinstance(rasgos, dict):
        for key in RASGOS:
            value = rasgos.get(key)
            try:
                clean[key] = round(min(1.0, max(0.0, float(value))), 2)
            except (TypeError, ValueError):
                continue
    return arq, clean


def format_psyche_line(meta: dict) -> str:
    """Línea conductual para el prompt a partir del frontmatter del NPC.

    Ej.: "psique: sombra (guarda secretos...; desconfiado) — agresividad
    alta, empatía baja". Cadena vacía si el NPC no tiene datos de psique.
    """
    if not isinstance(meta, dict):
        return ""
    arq, rasgos = validate_psyche(meta.get("arquetipo"), meta.get("rasgos"))
    partes = []
    if arq:
        partes.append(f"{arq} ({_CONDUCTA[arq]})")

    salientes = []
    for key in RASGOS:
        if key not in rasgos:
            continue
        if rasgos[key] >= _UMBRAL_ALTO:
            salientes.append(f"{key.replace('_', ' ')} alta")
        elif rasgos[key] <= _UMBRAL_BAJO:
            salientes.append(f"{key.replace('_', ' ')} baja")
    if salientes:
        partes.append(", ".join(salientes))

    return f"psique: {' — '.join(partes)}" if partes else ""
