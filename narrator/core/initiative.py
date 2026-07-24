"""
Cola de iniciativa — combate por turnos explícito, Python puro.

Modelo mínimo: agregar/quitar combatientes con su valor de iniciativa, orden
descendente, puntero de turno activo que rota y salta combatientes caídos.
No calcula iniciativa (eso lo resuelve el RuleArbiter/sistema) — esto solo
ordena y lleva la cuenta de a quién le toca.
"""

from dataclasses import dataclass


@dataclass
class Combatant:
    nombre: str
    iniciativa: int
    activo: bool = True  # False = caído/fuera de combate; se salta en next_turn


class InitiativeQueue:
    def __init__(self):
        self._combatants: "list[Combatant]" = []
        self._turn_index: int = 0
        self._round: int = 1

    # ── Gestión de combatientes ──────────────────────────────
    def add(self, nombre: str, iniciativa: int) -> None:
        """Agrega (o reemplaza si ya existía) un combatiente y reordena."""
        self.remove(nombre)
        self._combatants.append(Combatant(nombre=nombre, iniciativa=iniciativa))
        self._combatants.sort(key=lambda c: c.iniciativa, reverse=True)
        if self._turn_index >= len(self._combatants):
            self._turn_index = 0

    def remove(self, nombre: str) -> None:
        idx = self._find_index(nombre)
        if idx is None:
            return
        self._combatants.pop(idx)
        if not self._combatants:
            self._turn_index = 0
        elif idx < self._turn_index:
            self._turn_index -= 1
        elif self._turn_index >= len(self._combatants):
            self._turn_index = 0

    def set_active(self, nombre: str, activo: bool) -> None:
        """Marca un combatiente caído (activo=False): se salta en next_turn
        pero no se borra de la cola (puede reanimarse)."""
        c = self._find(nombre)
        if c:
            c.activo = activo

    # ── Turnos ─────────────────────────────────────────────────
    def order(self) -> "list[str]":
        return [c.nombre for c in self._combatants]

    def current_name(self) -> "str | None":
        if not self._combatants:
            return None
        return self._combatants[self._turn_index].nombre

    def round(self) -> int:
        return self._round

    def is_active(self) -> bool:
        return len(self._combatants) > 0

    def next_turn(self) -> "str | None":
        """Avanza al siguiente combatiente activo (salteando caídos). Si da
        la vuelta completa, incrementa la ronda UNA sola vez. Devuelve el
        nombre del turno activo, o None si nadie está activo."""
        n = len(self._combatants)
        if n == 0:
            return None
        start = self._turn_index
        wrapped = False
        for step in range(1, n + 1):
            idx = (start + step) % n
            if idx == 0 and not wrapped:
                self._round += 1
                wrapped = True
            if self._combatants[idx].activo:
                self._turn_index = idx
                return self.current_name()
        return None  # nadie activo

    def reset(self) -> None:
        self._combatants = []
        self._turn_index = 0
        self._round = 1

    # ── Serialización (para persistir en StateManager) ──────────
    def to_dict(self) -> dict:
        return {
            "combatientes": [
                {"nombre": c.nombre, "iniciativa": c.iniciativa, "activo": c.activo}
                for c in self._combatants
            ],
            "turno_index": self._turn_index,
            "ronda": self._round,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "InitiativeQueue":
        q = cls()
        q._combatants = [Combatant(**c) for c in data.get("combatientes", [])]
        q._turn_index = data.get("turno_index", 0)
        q._round = data.get("ronda", 1)
        return q

    # ── Internos ──────────────────────────────────────────────
    def _find(self, nombre: str) -> "Combatant | None":
        for c in self._combatants:
            if c.nombre == nombre:
                return c
        return None

    def _find_index(self, nombre: str) -> "int | None":
        for i, c in enumerate(self._combatants):
            if c.nombre == nombre:
                return i
        return None
