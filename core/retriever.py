"""
Vault Retriever — busca archivos en el vault y extrae contexto relevante.
El vault son archivos Markdown con frontmatter YAML.
"""

from pathlib import Path
from typing import Optional

try:
    import frontmatter as fm
    _HAS_FRONTMATTER = True
except ImportError:
    _HAS_FRONTMATTER = False


def _parse_file(path: Path) -> tuple[dict, str]:
    """Returns (metadata_dict, body_text). Graceful fallback si falta python-frontmatter."""
    text = path.read_text(encoding="utf-8", errors="ignore")
    if _HAS_FRONTMATTER:
        try:
            post = fm.loads(text)
            return dict(post.metadata), post.content
        except Exception:
            pass
    # Fallback: sin frontmatter
    return {}, text


class VaultRetriever:
    def __init__(self, vault_path: str = "./vault"):
        self.vault_path = Path(vault_path)

    def _all_md_files(self) -> list[Path]:
        if not self.vault_path.exists():
            return []
        return list(self.vault_path.rglob("*.md"))

    # ── Por tipo ──────────────────────────────────────────────
    def get_by_type(self, tipo: str, max_files: int = 10) -> list[dict]:
        """Devuelve todos los archivos del vault con el tipo dado (npc, locacion, frente…)"""
        results = []
        for path in self._all_md_files():
            meta, body = _parse_file(path)
            if meta.get("tipo") == tipo:
                results.append({"meta": meta, "body": body, "path": str(path)})
            if len(results) >= max_files:
                break
        return results

    # ── Búsqueda por keyword ──────────────────────────────────
    def search(self, query: str, max_results: int = 5) -> list[dict]:
        """Búsqueda por coincidencia de keywords. Devuelve por relevancia."""
        query_lower = query.lower()
        scored = []
        for path in self._all_md_files():
            meta, body = _parse_file(path)
            full_text = str(meta) + " " + body
            score = full_text.lower().count(query_lower)
            if score > 0:
                scored.append((score, {"meta": meta, "body": body, "path": str(path)}))
        scored.sort(reverse=True)
        return [item for _, item in scored[:max_results]]

    # ── Contexto compacto ─────────────────────────────────────
    def get_relevant_context(self, query: str, max_words: int = 400) -> str:
        """
        Devuelve un bloque de texto con contenido del vault relevante para la query.
        Se mantiene dentro del budget de palabras para no inflar el contexto del LLM.
        """
        results = self.search(query, max_results=3)
        if not results:
            # Fallback: resumen de NPCs y frentes activos
            results = (
                self.get_by_type("npc", max_files=2)
                + self.get_by_type("frente", max_files=2)
            )

        parts = []
        total_words = 0
        for r in results:
            meta = r["meta"]
            name = meta.get("nombre", Path(r["path"]).stem)
            tipo = meta.get("tipo", "entrada")
            body_snippet = r["body"][:600]
            snippet = f"[{tipo.upper()}] {name}\n{body_snippet}"
            words = len(snippet.split())
            if total_words + words > max_words:
                break
            parts.append(snippet)
            total_words += words

        return "\n---\n".join(parts) if parts else ""

    # ── Resúmenes de estado ───────────────────────────────────
    def get_active_npcs_summary(self, max_npcs: int = 6) -> str:
        """Resumen compacto de NPCs del vault para el contexto del narrador."""
        npcs = self.get_by_type("npc", max_files=max_npcs)
        if not npcs:
            return ""
        lines = []
        for npc in npcs:
            m = npc["meta"]
            name = m.get("nombre", "?")
            grupo = m.get("clan", m.get("raza", m.get("ocupacion", m.get("tipo", ""))))
            rol = m.get("rol", "")
            amenaza = m.get("amenaza", "")
            amenaza_str = f" [amenaza:{amenaza}]" if amenaza else ""
            lines.append(f"- {name} ({grupo}){amenaza_str}: {rol}")
        return "\n".join(lines)

    def get_active_fronts_summary(self) -> str:
        """Resumen de frentes activos para el contexto del narrador."""
        fronts = self.get_by_type("frente")
        if not fronts:
            return ""
        lines = []
        for f in fronts:
            m = f["meta"]
            name = m.get("nombre", "?")
            estado = m.get("estado", "?")
            escasez = m.get("escasez", "")
            lines.append(f"- {name} [{estado}]{': ' + escasez if escasez else ''}")
        return "\n".join(lines)

    def vault_is_empty(self) -> bool:
        return len(self._all_md_files()) == 0
