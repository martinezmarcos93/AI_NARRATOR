"""
Lorebook por keywords — RAG liviano sin embeddings.

Complementa (no reemplaza) la búsqueda semántica/keyword del vault: inyecta
fragmentos de reglas o notas específicas del sistema activo cuando el texto
del jugador/narrador contiene ciertas keywords. Útil cuando nomic-embed-text
no está instalado, o para reglas puntuales que conviene mencionar siempre
que aparezca el tema.

Formato esperado en `data/systems/<sistema>.yaml`:

    lorebook:
      - keywords: ["vaulderie", "lazo de sangre"]
        content: "La Vaulderie crea un lazo de sangre unilateral..."
        priority: 5
"""


def match_entries(entries: "list[dict]", text: str) -> "list[dict]":
    """Filtra las entradas cuyas keywords aparecen en `text` (case-insensitive)."""
    t = (text or "").lower()
    if not t:
        return []
    matched = []
    for entry in entries or []:
        keywords = entry.get("keywords") or []
        if any(str(kw).lower() in t for kw in keywords):
            matched.append(entry)
    return matched


def get_matching_content(entries: "list[dict]", text: str, max_words: int = 200) -> str:
    """Contenido de las entradas que matchean `text`, ordenadas por prioridad
    descendente, recortado a `max_words`. Cadena vacía si no hay match."""
    matched = match_entries(entries, text)
    matched.sort(key=lambda e: e.get("priority", 0), reverse=True)

    parts = []
    total_words = 0
    for entry in matched:
        content = str(entry.get("content", "")).strip()
        if not content:
            continue
        words = len(content.split())
        if total_words + words > max_words:
            continue
        parts.append(content)
        total_words += words

    return "\n---\n".join(parts)
