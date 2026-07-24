"""Tests del auto-guardado de entidades y mutación de estado (Fase 11):
etiquetas técnicas del narrador ([[NUEVO_NPC]]/[state: ...]) parseadas
en NarratorAgent y aplicadas al vault/ficha."""

from narrator.agents.narrator_agent import NarratorAgent
from narrator.core.vault_writer import VaultWriter


def _agent() -> NarratorAgent:
    return NarratorAgent()


# ── extract_new_entities ──────────────────────────────────────
def test_extract_nuevo_npc():
    texto = (
        "El mendigo te observa desde las sombras.\n\n"
        "[[NUEVO_NPC]]\n"
        "NOMBRE: Kael el Mendigo\n"
        "ROL: informante callejero\n"
        "AMENAZA: baja\n"
        "[[/NUEVO_NPC]]"
    )
    entidades = _agent().extract_new_entities(texto)
    assert entidades == [("npc", {
        "nombre": "Kael el Mendigo", "rol": "informante callejero", "amenaza": "baja",
    })]


def test_extract_nueva_locacion():
    texto = "[[NUEVA_LOCACION]]\nNOMBRE: El Muelle Viejo\nDISTRITO: Puerto\n[[/NUEVA_LOCACION]]"
    entidades = _agent().extract_new_entities(texto)
    assert entidades == [("locacion", {"nombre": "El Muelle Viejo", "distrito": "Puerto"})]


def test_extract_multiples_entidades():
    texto = (
        "[[NUEVO_NPC]]\nNOMBRE: Kael\n[[/NUEVO_NPC]]\n"
        "[[NUEVA_LOCACION]]\nNOMBRE: El Muelle\n[[/NUEVA_LOCACION]]"
    )
    entidades = _agent().extract_new_entities(texto)
    assert len(entidades) == 2
    assert entidades[0][0] == "npc"
    assert entidades[1][0] == "locacion"


def test_extract_bloque_sin_nombre_se_descarta():
    texto = "[[NUEVO_NPC]]\nROL: sin nombre\n[[/NUEVO_NPC]]"
    assert _agent().extract_new_entities(texto) == []


def test_extract_sin_bloques_devuelve_vacio():
    assert _agent().extract_new_entities("Narración normal sin etiquetas.") == []


# ── extract_state_mutations ───────────────────────────────────
def test_extract_mutacion_con_delta():
    texto = "El golpe conecta. [state: field=hp delta=-3 reason=herida de espada] Tambaleás."
    mutaciones = _agent().extract_state_mutations(texto)
    assert mutaciones == [{"field": "hp", "delta": "-3", "reason": "herida de espada"}]


def test_extract_mutacion_con_value():
    texto = "[state: field=estado value=envenenado reason=veneno de araña]"
    mutaciones = _agent().extract_state_mutations(texto)
    assert mutaciones[0]["field"] == "estado"
    assert mutaciones[0]["value"] == "envenenado"


def test_extract_multiples_mutaciones():
    texto = "[state: field=hp delta=-2] Seguís avanzando. [state: field=hambre delta=1]"
    mutaciones = _agent().extract_state_mutations(texto)
    assert len(mutaciones) == 2
    assert mutaciones[0]["field"] == "hp"
    assert mutaciones[1]["field"] == "hambre"


def test_extract_mutacion_sin_field_se_descarta():
    texto = "[state: delta=-3 reason=sin campo]"
    assert _agent().extract_state_mutations(texto) == []


def test_extract_sin_tags_devuelve_vacio():
    assert _agent().extract_state_mutations("Narración normal.") == []


# ── apply_state_mutations ─────────────────────────────────────
def test_apply_delta_sobre_valor_existente():
    char = {"hp": 12}
    changelog = _agent().apply_state_mutations(char, [{"field": "hp", "delta": "-3"}])
    assert char["hp"] == 9
    assert changelog == ["hp: 12 → 9"]


def test_apply_delta_sobre_campo_inexistente_asume_cero():
    char = {}
    _agent().apply_state_mutations(char, [{"field": "hambre", "delta": "2"}])
    assert char["hambre"] == 2


def test_apply_value_reemplaza_directo():
    char = {"estado": "sano"}
    changelog = _agent().apply_state_mutations(char, [{"field": "estado", "value": "envenenado"}])
    assert char["estado"] == "envenenado"
    assert "sano → envenenado" in changelog[0]


def test_apply_incluye_reason_en_el_log():
    char = {"hp": 10}
    changelog = _agent().apply_state_mutations(
        char, [{"field": "hp", "delta": "-5", "reason": "trampa de fuego"}]
    )
    assert "trampa de fuego" in changelog[0]


def test_apply_delta_invalido_no_rompe():
    char = {"hp": 10}
    changelog = _agent().apply_state_mutations(char, [{"field": "hp", "delta": "no-es-numero"}])
    assert char["hp"] == 10  # sin cambios
    assert changelog == []


def test_apply_sin_field_ni_delta_ni_value_se_ignora():
    char = {"hp": 10}
    changelog = _agent().apply_state_mutations(char, [{"field": "hp"}])
    assert changelog == []


# ── strip_system_tags ─────────────────────────────────────────
def test_strip_quita_bloque_de_entidad():
    texto = "Hola.\n[[NUEVO_NPC]]\nNOMBRE: Kael\n[[/NUEVO_NPC]]"
    assert "[[NUEVO_NPC]]" not in _agent().strip_system_tags(texto)
    assert "Hola." in _agent().strip_system_tags(texto)


def test_strip_quita_tag_de_estado_inline():
    texto = "El golpe conecta [state: field=hp delta=-3] y tambaleás."
    limpio = _agent().strip_system_tags(texto)
    assert "[state:" not in limpio
    assert "El golpe conecta" in limpio and "tambaleás." in limpio


def test_strip_sin_tags_no_modifica_el_texto():
    texto = "Narración limpia sin etiquetas técnicas."
    assert _agent().strip_system_tags(texto) == texto


def test_strip_normaliza_espacio_doble_dejado_por_el_tag():
    texto = "El golpe conecta. [state: field=hp delta=-3] El mendigo cae herido."
    limpio = _agent().strip_system_tags(texto)
    assert "  " not in limpio
    assert limpio == "El golpe conecta. El mendigo cae herido."


def test_strip_normaliza_lineas_en_blanco_de_mas():
    texto = "Narración.\n\n[[NUEVO_NPC]]\nNOMBRE: Kael\n[[/NUEVO_NPC]]"
    limpio = _agent().strip_system_tags(texto)
    assert "\n\n\n" not in limpio


# ── VaultWriter.create_npc / create_locacion ─────────────────
def test_create_npc_escribe_frontmatter(tmp_path):
    vw = VaultWriter(vault_path=str(tmp_path / "vault"))
    path = vw.create_npc({"nombre": "Kael el Mendigo", "rol": "informante", "amenaza": "baja"})
    assert path.exists()
    content = path.read_text(encoding="utf-8")
    assert "tipo: npc" in content
    assert "Kael el Mendigo" in content
    assert "auto-guardado" in content


def test_create_npc_no_pisa_uno_existente(tmp_path):
    vw = VaultWriter(vault_path=str(tmp_path / "vault"))
    p1 = vw.create_npc({"nombre": "Kael"})
    original = p1.read_text(encoding="utf-8")
    p2 = vw.create_npc({"nombre": "Kael", "rol": "otro rol totalmente distinto"})
    assert p2 is None
    assert p1.read_text(encoding="utf-8") == original  # no se tocó


def test_create_npc_sin_nombre_devuelve_none(tmp_path):
    vw = VaultWriter(vault_path=str(tmp_path / "vault"))
    assert vw.create_npc({"rol": "sin nombre"}) is None


def test_create_locacion_escribe_frontmatter(tmp_path):
    vw = VaultWriter(vault_path=str(tmp_path / "vault"))
    path = vw.create_locacion({"nombre": "El Muelle Viejo", "distrito": "Puerto"})
    assert path.exists()
    content = path.read_text(encoding="utf-8")
    assert "tipo: locacion" in content
    assert "El Muelle Viejo" in content
