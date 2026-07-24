"""
Detector de menciones — recall automático por nombre conocido en el mensaje
del jugador, sin comando explícito.

A diferencia de una regex ciega de "nombre propio capitalizado" (muchos
falsos positivos en español, donde toda oración empieza en mayúscula), esto
matchea contra una lista de nombres YA CONOCIDOS del vault (NPCs, Locaciones)
— substring case-insensitive, con preferencia por el apellido si el nombre
es compuesto (mismo criterio que ya usa VaultWriter para notas reactivas).
"""


def detect_mentions(text: str, known_names: "list[str]") -> "list[str]":
    """Devuelve los nombres de `known_names` mencionados en `text`
    (aparición literal, o de su última palabra si el nombre es compuesto).
    Preserva el orden de `known_names`, sin duplicados."""
    if not text or not known_names:
        return []
    text_lower = text.lower()
    mentioned = []
    for name in known_names:
        name_lower = str(name).lower().strip()
        if not name_lower:
            continue
        parts = name_lower.split()
        matched = name_lower in text_lower or (len(parts) > 1 and parts[-1] in text_lower)
        if matched and name not in mentioned:
            mentioned.append(name)
    return mentioned
