"""
Reparación best-effort de JSON malformado devuelto por un LLM local.

No reemplaza json.loads: se usa como segundo intento cuando el parseo directo
falla, antes de descartar la respuesta. Heurísticas encadenadas:
- comas colgantes antes de un cierre (",}" / ",]")
- campos numéricos con texto pegado (ej. '"nivel": 5 aprox,' -> '"nivel": 5,')
- llaves/corchetes sin cerrar por truncamiento (max_tokens cortó la respuesta
  a mitad de generación), ignorando el contenido de strings.

Nunca eval/exec: solo transformaciones de texto seguidas de json.loads.
"""

import json
import re

from narrator.logger import logger

_RE_TRAILING_COMMA = re.compile(r",\s*([}\]])")
_RE_NUMERIC_GARBAGE = re.compile(r':\s*(-?\d+(?:\.\d+)?)\s+[^",{\[\]\d][^,}\]]*(?=[,}\]])')


def _strip_trailing_commas(text: str) -> str:
    return _RE_TRAILING_COMMA.sub(r"\1", text)


def _strip_numeric_garbage(text: str) -> str:
    return _RE_NUMERIC_GARBAGE.sub(lambda m: f": {m.group(1)}", text)


def _balance_brackets(text: str) -> str:
    """Agrega los cierres faltantes al final del texto. Recorre carácter a
    carácter ignorando el contenido de strings (para no contar llaves que
    aparezcan dentro de un campo narrativo, ej. una descripción)."""
    stack = []
    in_string = False
    escape = False
    for ch in text:
        if in_string:
            if escape:
                escape = False
            elif ch == "\\":
                escape = True
            elif ch == '"':
                in_string = False
            continue
        if ch == '"':
            in_string = True
        elif ch in "{[":
            stack.append(ch)
        elif ch in "}]":
            if stack and ((ch == "}" and stack[-1] == "{") or (ch == "]" and stack[-1] == "[")):
                stack.pop()
    closers = {"{": "}", "[": "]"}
    return text + "".join(closers[c] for c in reversed(stack))


def repair(text: str) -> str:
    """Aplica las heurísticas de reparación en cadena. El resultado puede
    seguir sin ser JSON válido si el daño es más profundo que esto.

    Orden importante: balancear llaves puede crear una coma colgante nueva
    justo antes del cierre agregado (ej. '..."Mago",' -> '..."Mago",}'), así
    que la limpieza de comas colgantes va DESPUÉS del balanceo, no antes."""
    candidate = text.strip()
    candidate = _strip_numeric_garbage(candidate)
    candidate = _balance_brackets(candidate)
    candidate = _strip_trailing_commas(candidate)
    return candidate


def try_parse(text: str, retries: int = 1):
    """Intenta json.loads(text); si falla, repara y reintenta hasta `retries`
    veces. Devuelve el objeto parseado, o None si no se pudo recuperar."""
    if not text:
        return None
    candidate = text
    for attempt in range(retries + 1):
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            if attempt >= retries:
                break
            candidate = repair(candidate)
    logger.error(f"json_repair: no se pudo recuperar JSON tras reparación: {text[:200]!r}")
    return None
