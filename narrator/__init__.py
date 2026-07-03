"""AI Narrator — Motor de Rol con Agentes y Ollama."""

from pathlib import Path

__version__ = "0.2.0"
PROJECT_ROOT = Path(__file__).parent.parent  # narrator/ → repo root


def resolve_path(p: "str | Path") -> Path:
    """Resuelve una ruta relativa contra la raíz del proyecto.
    Evita que vault/, estado_campana.yaml, etc. se creen en el CWD
    cuando la app se ejecuta desde otro directorio."""
    p = Path(p)
    return p if p.is_absolute() else PROJECT_ROOT / p
