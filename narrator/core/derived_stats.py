"""
DSL seguro para estadísticas derivadas en YAML de sistema.
Vocabulario fijo (copy_of, half_of, floor_div, sum_of, computer) — nunca eval/exec.
"""

import math
from typing import Any, Callable

_REGISTRY: dict[str, Callable[[dict], Any]] = {}


class DerivedStatError(ValueError):
    """Spec de stat derivado inválida, o referencia a un campo/función inexistente."""


def register_computer(name: str):
    """Decorador: registra una función Python nombrada, invocable desde YAML vía {"computer": name}."""

    def deco(fn: Callable[[dict], Any]) -> Callable[[dict], Any]:
        _REGISTRY[name] = fn
        return fn

    return deco


def _get_field(data: dict, key: str) -> Any:
    if key not in data:
        raise DerivedStatError(f"Campo desconocido referenciado en stat derivado: '{key}'")
    return data[key]


def _as_number(value: Any, key: str) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        raise DerivedStatError(f"Campo '{key}' no es numérico (valor: {value!r})")


def evaluate(spec: dict, data: dict) -> Any:
    """Evalúa un nodo del DSL contra `data`. Lanza DerivedStatError ante cualquier ambigüedad."""
    if not isinstance(spec, dict) or not spec:
        raise DerivedStatError(f"Spec de stat derivado inválida: {spec!r}")

    if "copy_of" in spec:
        return _get_field(data, spec["copy_of"])

    if "half_of" in spec:
        key = spec["half_of"]
        value = _as_number(_get_field(data, key), key)
        if spec.get("round") == "ceil":
            return math.ceil(value / 2)
        return int(value // 2)

    if "floor_div" in spec:
        key = spec["floor_div"]
        value = _as_number(_get_field(data, key), key)
        divisor = spec.get("divisor", 1)
        if divisor == 0:
            raise DerivedStatError("floor_div: 'divisor' no puede ser 0")
        offset = spec.get("offset", 0)
        return int((value + offset) // divisor)

    if "sum_of" in spec:
        keys = spec["sum_of"]
        if not isinstance(keys, list) or not keys:
            raise DerivedStatError("sum_of requiere una lista no vacía de campos")
        total = sum(_as_number(_get_field(data, k), k) for k in keys)
        return int(total) if total == int(total) else total

    if "computer" in spec:
        name = spec["computer"]
        fn = _REGISTRY.get(name)
        if fn is None:
            raise DerivedStatError(f"No hay función registrada para computer='{name}'")
        return fn(data)

    raise DerivedStatError(f"Operador desconocido en spec de stat derivado: {list(spec.keys())!r}")


def evaluate_all(derived_specs: dict, data: dict) -> dict:
    """Evalúa todas las claves de `derived_specs` contra `data`.
    Cada derivado calculado queda disponible para los siguientes (permite encadenar)."""
    result: dict = {}
    working = dict(data)
    for key, spec in derived_specs.items():
        value = evaluate(spec, working)
        result[key] = value
        working[key] = value
    return result
