"""
State Manager — gestiona estado_campana.yaml.
Relojes de frentes, flags de eventos, historial de sesiones, escena actual.
"""

import yaml
from narrator.logger import logger
from pathlib import Path
from datetime import datetime
from typing import Any, Optional


class StateManager:
    def __init__(self, state_path: str = "./estado_campana.yaml"):
        self.path = Path(state_path)
        self.data: dict = self._default()

    def _default(self) -> dict:
        return {
            "meta": {
                "sistema": "generic",
                "campana": "Sin nombre",
                "ciudad": "",
                "sesion_actual": 0,
                "fecha_inicio": None,
                "ultima_sesion": None,
            },
            "escena_actual": {
                "locacion": None,
                "npcs_presentes": [],
                "turno_narrativo": 0,
            },
            "relojes": {},
            "flags": {},
            "escenas": {},
            "downtime": {"pendiente": [], "npcs_activos": []},
            "historial": [],
        }

    # ── Persistencia ──────────────────────────────────────────
    def load(self) -> bool:
        if not self.path.exists():
            return False
        try:
            with open(self.path, encoding="utf-8") as f:
                loaded = yaml.safe_load(f) or {}
            # Deep merge sobre el default para no perder claves nuevas
            merged = self._default()
            for key, val in loaded.items():
                if isinstance(val, dict) and key in merged:
                    merged[key].update(val)
                else:
                    merged[key] = val
            self.data = merged
            return True
        except Exception as e:
            # Estado corrupto: backup antes de que el próximo save() lo pise.
            logger.error(f"estado_campana.yaml corrupto o ilegible: {e}", exc_info=True)
            backup = self.path.with_name(
                f"{self.path.stem}.corrupto-{datetime.now():%Y%m%d-%H%M%S}{self.path.suffix}"
            )
            try:
                self.path.rename(backup)
                logger.error(f"Backup del estado corrupto guardado en: {backup}")
            except OSError as be:
                logger.error(f"No pude hacer backup del estado corrupto: {be}")
            return False

    def save(self):
        with open(self.path, "w", encoding="utf-8") as f:
            yaml.dump(self.data, f, allow_unicode=True, default_flow_style=False, sort_keys=False)

    # ── Escena actual ─────────────────────────────────────────
    def set_location(self, loc: str):
        self.data["escena_actual"]["locacion"] = loc

    def get_location(self) -> Optional[str]:
        return self.data["escena_actual"].get("locacion")

    def add_npc_to_scene(self, name: str):
        present = self.data["escena_actual"].setdefault("npcs_presentes", [])
        if name not in present:
            present.append(name)

    def clear_scene(self):
        self.data["escena_actual"]["npcs_presentes"] = []
        self.data["escena_actual"]["turno_narrativo"] = 0

    def increment_turn(self):
        sc = self.data["escena_actual"]
        sc["turno_narrativo"] = sc.get("turno_narrativo", 0) + 1

    # ── Relojes (Fronts clocks) ───────────────────────────────
    def add_clock(self, name: str, segments: int = 6, description: str = ""):
        self.data["relojes"][name] = {
            "segmentos": segments,
            "llenos": 0,
            "descripcion": description,
        }
        self.save()

    def advance_clock(self, name: str, n: int = 1) -> dict:
        """Avanza un reloj n segmentos. Devuelve estado actual."""
        clock = self.data["relojes"].get(name)
        if not clock:
            return {}
        clock["llenos"] = min(clock["llenos"] + n, clock["segmentos"])
        self.save()
        return clock

    def is_clock_full(self, name: str) -> bool:
        clock = self.data["relojes"].get(name, {})
        return clock.get("llenos", 0) >= clock.get("segmentos", 6)

    def get_clocks_summary(self) -> str:
        """Texto compacto de todos los relojes para el contexto."""
        relojes = self.data.get("relojes", {})
        if not relojes:
            return ""
        lines = []
        for name, c in relojes.items():
            bar = "█" * c.get("llenos", 0) + "░" * (c.get("segmentos", 6) - c.get("llenos", 0))
            lines.append(f"  {name}: [{bar}] {c.get('descripcion', '')}")
        return "\n".join(lines)

    # ── Flags de eventos ──────────────────────────────────────
    def set_flag(self, name: str, value: Any, description: str = ""):
        self.data["flags"][name] = {
            "valor": value,
            "descripcion": description,
            "sesion": self.data["meta"].get("sesion_actual", 0),
        }
        self.save()

    def get_flag(self, name: str, default: Any = None) -> Any:
        entry = self.data["flags"].get(name)
        return entry["valor"] if entry else default

    # ── Escenas (C2 — patrón contenido/estado de rage_war) ────
    # El contenido de cada escena vive en el vault (Escenas/*.md);
    # acá solo se persiste su estado: bloqueada → disponible → jugada.
    def get_scene_state(self, name: str) -> dict:
        return self.data.setdefault("escenas", {}).get(
            name, {"estado": "bloqueada", "desbloqueada_por": ""})

    def set_scene_state(self, name: str, estado: str, por: str = ""):
        escenas = self.data.setdefault("escenas", {})
        entry = escenas.setdefault(name, {"estado": "bloqueada", "desbloqueada_por": ""})
        entry["estado"] = estado
        if por:
            entry["desbloqueada_por"] = por
        self.save()

    def get_scenes_by_state(self, estado: str) -> "list[str]":
        return [n for n, e in self.data.get("escenas", {}).items()
                if e.get("estado") == estado]

    # ── Historial de sesiones ─────────────────────────────────
    def start_session(self):
        self.data["meta"]["sesion_actual"] = self.data["meta"].get("sesion_actual", 0) + 1
        self.data["meta"]["ultima_sesion"] = datetime.now().isoformat()
        self.save()

    def add_session_summary(
        self,
        resumen: str,
        decisiones: list[str] = None,
        consecuencias: list[str] = None,
    ):
        self.data["historial"].append({
            "sesion": self.data["meta"].get("sesion_actual", 0),
            "resumen": resumen,
            "decisiones_clave": decisiones or [],
            "consecuencias_plantadas": consecuencias or [],
        })
        self.save()

    def get_last_session_summary(self) -> str:
        hist = self.data.get("historial", [])
        if not hist:
            return ""
        last = hist[-1]
        return f"Sesión {last['sesion']}: {last['resumen']}"

    def get_session_number(self) -> int:
        return self.data["meta"].get("sesion_actual", 0)

    # ── Frentes (gestión programática) ───────────────────────
    def add_front(self, name: str, description: str = "", max_stage: int = 6) -> None:
        """Registra un frente como reloj si no existe todavía."""
        if name not in self.data["relojes"]:
            self.data["relojes"][name] = {
                "segmentos": max_stage,
                "llenos": 0,
                "descripcion": description,
            }
            self.save()

    def advance_front_clock(self, name: str, ticks: int = 1) -> None:
        """Avanza el reloj de un frente registrado."""
        clock = self.data["relojes"].get(name)
        if clock:
            clock["llenos"] = min(clock["llenos"] + ticks, clock["segmentos"])
            self.save()

    # ── Downtime entre sesiones ───────────────────────────────
    def add_downtime_action(self, actor: str, action: str):
        self.data["downtime"].setdefault("pendiente", []).append({
            "actor": actor, "accion": action
        })
        self.save()

    def add_active_npc(self, npc_name: str, action: str):
        self.data["downtime"].setdefault("npcs_activos", []).append({
            "npc": npc_name, "accion": action
        })
        self.save()

    def clear_downtime(self):
        self.data["downtime"] = {"pendiente": [], "npcs_activos": []}
        self.save()
