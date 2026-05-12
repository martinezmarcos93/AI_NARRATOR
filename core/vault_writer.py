"""
Vault Writer — escribe al vault en tiempo real durante la sesión.
Cada respuesta del narrador actualiza el log de sesión, las notas de NPCs
y el estado de campaña. Obsidian lo ve automáticamente al refrescar.
"""

import re
from datetime import datetime
from pathlib import Path
from typing import Optional


class VaultWriter:
    def __init__(self, vault_path: str = "./vault"):
        self.vault = Path(vault_path)
        self._session_file: Optional[Path] = None
        self._npc_cache: dict[str, Path] = {}   # nombre_lower → Path del archivo
        self._loc_cache: dict[str, Path] = {}

    # ── Inicialización de sesión ──────────────────────────────
    def start_session(self, session_number: int, system_name: str, campaign_name: str = ""):
        """
        Crea el archivo de log de la sesión actual.
        Llamar una vez al inicio de cada sesión de juego.
        """
        sessions_dir = self.vault / "Sesiones"
        sessions_dir.mkdir(parents=True, exist_ok=True)

        date_str = datetime.now().strftime("%Y-%m-%d")
        filename = f"Sesion_{session_number:02d}_{date_str}.md"
        self._session_file = sessions_dir / filename

        if not self._session_file.exists():
            header = (
                f"---\n"
                f"tipo: sesion\n"
                f"sesion: {session_number}\n"
                f'fecha: "{date_str}"\n'
                f'sistema: "{system_name}"\n'
                f'campana: "{campaign_name}"\n'
                f'tags: ["sesion"]\n'
                f"---\n\n"
                f"# Sesión {session_number} — {date_str}\n\n"
                f"## Log\n\n"
            )
            self._session_file.write_text(header, encoding="utf-8")

        # Poblar caches de entidades conocidas
        self._refresh_entity_cache()

    def _refresh_entity_cache(self):
        """Carga en memoria los nombres de NPCs y Locaciones del vault."""
        self._npc_cache = {}
        self._loc_cache = {}
        for path in (self.vault / "NPCs").glob("*.md"):
            name = path.stem.replace("_", " ").lower()
            self._npc_cache[name] = path
        for path in (self.vault / "Locaciones").glob("*.md"):
            name = path.stem.replace("_", " ").lower()
            self._loc_cache[name] = path

    # ── Escritura de log de sesión ────────────────────────────
    def log_exchange(self, player_text: str, narrator_text: str):
        """
        Añade un intercambio completo (jugador + narrador) al log de sesión.
        """
        if not self._session_file:
            return
        timestamp = datetime.now().strftime("%H:%M")
        entry = (
            f"\n### [{timestamp}]\n\n"
            f"**Jugador:** {player_text.strip()}\n\n"
            f"**Narrador:** {narrator_text.strip()}\n\n"
            f"---\n"
        )
        with open(self._session_file, "a", encoding="utf-8") as f:
            f.write(entry)

    def log_dice_roll(self, roll_str: str):
        """Registra una tirada de dados en el log de sesión."""
        if not self._session_file:
            return
        timestamp = datetime.now().strftime("%H:%M")
        with open(self._session_file, "a", encoding="utf-8") as f:
            f.write(f"> 🎲 [{timestamp}] {roll_str}\n\n")

    def log_event(self, event_text: str):
        """Registra un evento importante en el log de sesión."""
        if not self._session_file:
            return
        timestamp = datetime.now().strftime("%H:%M")
        with open(self._session_file, "a", encoding="utf-8") as f:
            f.write(f"> ⚡ [{timestamp}] {event_text}\n\n")

    # ── Actualización de notas de NPCs ────────────────────────
    def _detect_mentioned_entities(self, text: str, cache: dict) -> list[Path]:
        """
        Busca en el texto los nombres de entidades conocidas del vault.
        Devuelve las rutas de archivos de las que aparecen mencionadas.
        """
        text_lower = text.lower()
        mentioned = []
        for name, path in cache.items():
            # Buscar nombre completo o apellido (última palabra si tiene más de una)
            parts = name.split()
            if name in text_lower or (len(parts) > 1 and parts[-1] in text_lower):
                if path not in mentioned:
                    mentioned.append(path)
        return mentioned

    def _append_to_section(self, file_path: Path, section_header: str, note: str):
        """
        Añade `note` al final de la sección `section_header` en un archivo MD.
        Si la sección no existe, la crea al final del archivo.
        """
        try:
            content = file_path.read_text(encoding="utf-8")
        except FileNotFoundError:
            return

        if section_header in content:
            # Insertar antes del siguiente ## o al final
            pattern = rf"({re.escape(section_header)})(.*?)(?=\n## |\Z)"
            match = re.search(pattern, content, re.DOTALL)
            if match:
                new_section = match.group(1) + match.group(2).rstrip() + "\n" + note + "\n"
                content = content[:match.start()] + new_section + content[match.end():]
            else:
                content += "\n" + note
        else:
            content += f"\n{section_header}\n\n{note}\n"

        file_path.write_text(content, encoding="utf-8")

    def update_npc_notes(self, narrator_text: str, session_number: int):
        """
        Detecta NPCs mencionados en la respuesta y añade una nota en
        su sección 'Notas de Sesión'.
        """
        mentioned = self._detect_mentioned_entities(narrator_text, self._npc_cache)
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
        session_ref = f"[[Sesion_{session_number:02d}]]"

        for npc_path in mentioned:
            # Extraer la primera oración del texto donde se menciona al NPC
            npc_name = npc_path.stem.replace("_", " ")
            # Buscar la frase que lo menciona
            sentences = re.split(r'[.!?]', narrator_text)
            relevant = next(
                (s.strip() for s in sentences if npc_name.lower() in s.lower()),
                ""
            )
            if not relevant:
                continue
            note = f"- {session_ref} ({timestamp}): {relevant[:150]}"
            self._append_to_section(npc_path, "## Notas de Sesión", note)

    def update_location_notes(self, narrator_text: str, session_number: int):
        """
        Detecta locaciones mencionadas y añade una nota en su archivo.
        """
        mentioned = self._detect_mentioned_entities(narrator_text, self._loc_cache)
        if not mentioned:
            return

        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
        session_ref = f"[[Sesion_{session_number:02d}]]"

        for loc_path in mentioned[:2]:  # máximo 2 locaciones por respuesta
            note = f"- {session_ref} ({timestamp}): escena activa"
            self._append_to_section(loc_path, "## Notas de Sesión", note)

    # ── Actualización del Dashboard ───────────────────────────
    def update_dashboard_state(
        self,
        location: str = "",
        session_number: int = 0,
        active_fronts_summary: str = "",
    ):
        """
        Actualiza el bloque de estado en el Dashboard.
        Busca el marcador <!-- estado --> y reemplaza hasta el siguiente <!-- /estado -->.
        Si no existe el marcador, no modifica el archivo.
        """
        dashboard = self.vault / "00_Dashboard.md"
        if not dashboard.exists():
            return

        content = dashboard.read_text(encoding="utf-8")
        date_str = datetime.now().strftime("%Y-%m-%d %H:%M")

        nuevo_estado = (
            f"<!-- estado -->\n"
            f"**Sesión:** {session_number} | **Última actualización:** {date_str}\n\n"
            f"**Locación actual:** {location or 'No definida'}\n\n"
            + (f"**Frentes activos:**\n{active_fronts_summary}\n\n" if active_fronts_summary else "")
            + f"<!-- /estado -->"
        )

        if "<!-- estado -->" in content and "<!-- /estado -->" in content:
            content = re.sub(
                r"<!-- estado -->.*?<!-- /estado -->",
                nuevo_estado,
                content,
                flags=re.DOTALL,
            )
            dashboard.write_text(content, encoding="utf-8")

    # ── Entry point principal ─────────────────────────────────
    def on_narrator_response(
        self,
        player_text: str,
        narrator_text: str,
        session_number: int = 1,
        is_important: bool = False,
    ):
        """
        Punto de entrada principal. Llamar después de cada respuesta del narrador.
        Actualiza log de sesión + notas de NPCs + notas de locaciones.
        """
        self.log_exchange(player_text, narrator_text)

        if is_important:
            first_sentence = re.split(r'[.!?\n]', narrator_text.strip())[0]
            self.log_event(first_sentence[:200])

        self.update_npc_notes(narrator_text, session_number)
        self.update_location_notes(narrator_text, session_number)
