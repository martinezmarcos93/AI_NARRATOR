"""Test Fase 18: búsqueda global cross-entidad en el vault."""

from narrator.core.retriever import VaultRetriever


def _write(vault, subdir, filename, frontmatter_lines, body="Cuerpo."):
    d = vault / subdir
    d.mkdir(parents=True, exist_ok=True)
    content = "---\n" + "\n".join(frontmatter_lines) + "\n---\n\n" + body + "\n"
    (d / filename).write_text(content, encoding="utf-8")


def _vault(tmp_path):
    v = tmp_path / "vault"
    _write(v, "NPCs", "Kael.md", ["tipo: npc", 'nombre: "Kael el Mendigo"'],
           "Conoce el puerto como nadie.")
    _write(v, "Locaciones", "Muelle.md", ["tipo: locacion", 'nombre: "El Muelle Viejo"'],
           "Cerca del puerto, siempre hay contrabando.")
    _write(v, "Cofradias", "Parias.md", ["tipo: cofradia", 'nombre: "Los Parias"'],
           "Controlan el mercado negro, lejos del puerto.")
    return v


def test_busqueda_devuelve_multiples_tipos(tmp_path):
    r = VaultRetriever(vault_path=str(_vault(tmp_path)))
    resultados = r.search_all("puerto")
    tipos = {res["tipo"] for res in resultados}
    assert tipos == {"npc", "locacion", "cofradia"}
    assert len(resultados) == 3


def test_busqueda_filtrada_por_tipo(tmp_path):
    r = VaultRetriever(vault_path=str(_vault(tmp_path)))
    resultados = r.search_all("puerto", tipo="npc")
    assert len(resultados) == 1
    assert resultados[0]["nombre"] == "Kael el Mendigo"


def test_busqueda_sin_resultados(tmp_path):
    r = VaultRetriever(vault_path=str(_vault(tmp_path)))
    assert r.search_all("inexistente xyz") == []


def test_busqueda_query_vacia(tmp_path):
    r = VaultRetriever(vault_path=str(_vault(tmp_path)))
    assert r.search_all("") == []
    assert r.search_all("   ") == []


def test_busqueda_case_insensitive(tmp_path):
    r = VaultRetriever(vault_path=str(_vault(tmp_path)))
    assert len(r.search_all("PUERTO")) == 3


def test_busqueda_ordena_por_score_descendente(tmp_path):
    v = tmp_path / "vault"
    _write(v, "NPCs", "A.md", ["tipo: npc", 'nombre: "A"'], "cripta cripta cripta")
    _write(v, "NPCs", "B.md", ["tipo: npc", 'nombre: "B"'], "cripta")
    r = VaultRetriever(vault_path=str(v))
    resultados = r.search_all("cripta")
    assert resultados[0]["nombre"] == "A"
