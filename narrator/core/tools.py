"""
Decorador @tool — genera schema de function-calling desde type hints +
docstring. Infraestructura pura: NO se conecta todavía al flujo de
prompting real (Orchestrator/PromptBuilder siguen como están). Sienta la
base para si algún día se migra de prompts monolíticos a function-calling
explícito, formalizando qué puede ver/hacer el LLM narrador vs el
RuleArbiter.

keeper_only: la herramienta expone datos que el narrador nunca debería
filtrar directo al jugador (ej. secretos de un Misterio) — se excluye por
defecto de la lista ofrecida al LLM narrador.
gated: nombre de una condición/skill que debe estar activa para que la
herramienta esté disponible (None = siempre disponible). Solo se guarda
el nombre acá; la resolución de si está "gateada" queda para quien
consuma el registro.
"""

import inspect
from typing import Callable, Dict, List, Optional, Union, get_args, get_origin, get_type_hints

_TYPE_MAP = {
    str: "string",
    int: "integer",
    float: "number",
    bool: "boolean",
}

_REGISTRY: "dict[str, ToolSpec]" = {}


def _json_type_for(annotation) -> str:
    origin = get_origin(annotation)
    if origin is Union:
        args = [a for a in get_args(annotation) if a is not type(None)]
        if len(args) == 1:
            return _json_type_for(args[0])
        return "string"  # unión compleja: fallback conservador
    # get_origin(list) es None (solo devuelve algo con genéricos parametrizados
    # como list[int]) — hay que contemplar también el tipo builtin "pelado".
    effective = origin or annotation
    if effective in (list, List):
        return "array"
    if effective in (dict, Dict):
        return "object"
    return _TYPE_MAP.get(effective, "string")


class ToolSpec:
    """Envoltorio de una función registrada: mantiene la función original
    invocable y su schema JSON generado."""

    def __init__(self, fn: Callable, name: str, description: str,
                 properties: dict, required: "list[str]",
                 keeper_only: bool, gated: "str | None"):
        self.fn = fn
        self.name = name
        self.description = description
        self.properties = properties
        self.required = required
        self.keeper_only = keeper_only
        self.gated = gated

    def __call__(self, *args, **kwargs):
        return self.fn(*args, **kwargs)

    def to_schema(self) -> dict:
        """Schema estilo function-calling (compatible con el formato usado
        por Ollama/OpenAI: name/description/parameters)."""
        return {
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "object",
                "properties": self.properties,
                "required": self.required,
            },
        }


def tool(keeper_only: bool = False, gated: "str | None" = None):
    """Decorador: registra `fn` como ToolSpec y genera su schema JSON
    automáticamente desde sus type hints + la primera línea del docstring."""

    def decorator(fn: Callable) -> ToolSpec:
        hints = get_type_hints(fn)
        sig = inspect.signature(fn)
        properties = {}
        required = []
        for pname, param in sig.parameters.items():
            if pname == "self":
                continue
            annotation = hints.get(pname, str)
            properties[pname] = {"type": _json_type_for(annotation)}
            if param.default is inspect.Parameter.empty:
                required.append(pname)

        description = (fn.__doc__ or "").strip().split("\n")[0]
        spec = ToolSpec(
            fn=fn,
            name=fn.__name__,
            description=description,
            properties=properties,
            required=required,
            keeper_only=keeper_only,
            gated=gated,
        )
        _REGISTRY[spec.name] = spec
        return spec

    return decorator


def get_registered_tools(include_keeper_only: bool = False) -> "list[ToolSpec]":
    """Herramientas registradas. Excluye keeper_only por defecto: son para
    el motor, nunca deberían ofrecerse directo al LLM narrador."""
    return [t for t in _REGISTRY.values() if include_keeper_only or not t.keeper_only]


def get_tool(name: str) -> "ToolSpec | None":
    return _REGISTRY.get(name)


def clear_registry() -> None:
    """Solo para tests: vacía el registro global entre casos."""
    _REGISTRY.clear()


# ── Ejemplos de validación del patrón (Fase 9) ────────────────────
# Stubs deliberados: NO están conectados a StateManager/vault todavía.
# Solo demuestran que el decorador genera un schema correcto sobre
# funciones con forma "de negocio" real, no juguetes triviales.

@tool()
def consultar_reloj_frente(nombre_frente: str) -> str:
    """Devuelve el estado del reloj de un frente activo por nombre."""
    return f"[stub] estado del reloj de '{nombre_frente}' no conectado aún."


@tool(keeper_only=True)
def consultar_secreto_npc(nombre_npc: str, detalle: Optional[str] = None) -> str:
    """Devuelve el secreto oculto de un NPC — solo para el motor, nunca directo al narrador."""
    return f"[stub] secreto de '{nombre_npc}' no conectado aún."
