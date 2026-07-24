"""Tests del decorador @tool — generación de schema desde type hints + docstring."""

from typing import Optional

import pytest

from narrator.core.tools import clear_registry, get_registered_tools, get_tool, tool


@pytest.fixture(autouse=True)
def _registro_limpio():
    """Aísla cada test: limpia el registro global antes y después."""
    clear_registry()
    yield
    clear_registry()


# ── generación de schema por tipo ────────────────────────────────
def test_tipos_basicos_str_int_bool_float():
    @tool()
    def ejemplo(nombre: str, cantidad: int, activo: bool, factor: float) -> str:
        """Descripción de ejemplo."""
        return "x"

    schema = ejemplo.to_schema()
    props = schema["parameters"]["properties"]
    assert props["nombre"] == {"type": "string"}
    assert props["cantidad"] == {"type": "integer"}
    assert props["activo"] == {"type": "boolean"}
    assert props["factor"] == {"type": "number"}


def test_lista_y_dict():
    @tool()
    def ejemplo(items: list, datos: dict) -> str:
        """Doc."""
        return "x"

    props = ejemplo.to_schema()["parameters"]["properties"]
    assert props["items"] == {"type": "array"}
    assert props["datos"] == {"type": "object"}


def test_lista_y_dict_parametrizados():
    @tool()
    def ejemplo(items: "list[int]", datos: "dict[str, int]") -> str:
        """Doc."""
        return "x"

    props = ejemplo.to_schema()["parameters"]["properties"]
    assert props["items"] == {"type": "array"}
    assert props["datos"] == {"type": "object"}


def test_optional_no_es_requerido_y_usa_tipo_interno():
    @tool()
    def ejemplo(nombre: str, apodo: Optional[str] = None) -> str:
        """Doc."""
        return "x"

    schema = ejemplo.to_schema()
    assert schema["parameters"]["properties"]["apodo"] == {"type": "string"}
    assert "apodo" not in schema["parameters"]["required"]
    assert "nombre" in schema["parameters"]["required"]


def test_parametro_sin_type_hint_usa_string_por_defecto():
    @tool()
    def ejemplo(algo) -> str:
        """Doc."""
        return "x"

    props = ejemplo.to_schema()["parameters"]["properties"]
    assert props["algo"] == {"type": "string"}


def test_self_se_ignora_en_metodos():
    class Clase:
        @tool()
        def metodo(self, nombre: str) -> str:
            """Doc."""
            return nombre

    schema = Clase.metodo.to_schema()
    assert "self" not in schema["parameters"]["properties"]
    assert list(schema["parameters"]["properties"]) == ["nombre"]


# ── description desde docstring ─────────────────────────────────
def test_description_toma_primera_linea_del_docstring():
    @tool()
    def ejemplo() -> str:
        """Primera línea.
        Segunda línea con más detalle que no debe entrar en description.
        """
        return "x"

    assert ejemplo.to_schema()["description"] == "Primera línea."


def test_sin_docstring_description_vacia():
    @tool()
    def ejemplo() -> str:
        return "x"

    assert ejemplo.to_schema()["description"] == ""


# ── name desde __name__ de la función ────────────────────────────
def test_name_es_el_nombre_de_la_funcion():
    @tool()
    def mi_herramienta_especial() -> str:
        """Doc."""
        return "x"

    assert mi_herramienta_especial.to_schema()["name"] == "mi_herramienta_especial"


# ── la función original sigue siendo invocable ───────────────────
def test_toolspec_es_invocable():
    @tool()
    def sumar(a: int, b: int) -> int:
        """Suma dos números."""
        return a + b

    assert sumar(2, 3) == 5


# ── keeper_only / gated ──────────────────────────────────────────
def test_keeper_only_excluido_por_defecto():
    @tool(keeper_only=True)
    def secreto() -> str:
        """Doc."""
        return "x"

    @tool()
    def publico() -> str:
        """Doc."""
        return "x"

    visibles = get_registered_tools()
    nombres = [t.name for t in visibles]
    assert "publico" in nombres
    assert "secreto" not in nombres


def test_keeper_only_incluido_si_se_pide_explicitamente():
    @tool(keeper_only=True)
    def secreto() -> str:
        """Doc."""
        return "x"

    nombres = [t.name for t in get_registered_tools(include_keeper_only=True)]
    assert "secreto" in nombres


def test_gated_se_guarda_en_el_spec():
    @tool(gated="skill_investigacion")
    def solo_con_skill() -> str:
        """Doc."""
        return "x"

    assert get_tool("solo_con_skill").gated == "skill_investigacion"


def test_gated_por_defecto_es_none():
    @tool()
    def sin_gate() -> str:
        """Doc."""
        return "x"

    assert get_tool("sin_gate").gated is None


# ── registro global ───────────────────────────────────────────────
def test_get_tool_devuelve_none_si_no_existe():
    assert get_tool("no_registrada") is None


def test_ejemplos_de_validacion_del_modulo_se_registran():
    # Importar el módulo real (no un ejemplo ad-hoc del test) para
    # confirmar que consultar_reloj_frente/consultar_secreto_npc
    # quedan bien formados end-to-end.
    clear_registry()
    import importlib

    import narrator.core.tools as tools_mod
    importlib.reload(tools_mod)

    publicas = [t.name for t in tools_mod.get_registered_tools()]
    todas = [t.name for t in tools_mod.get_registered_tools(include_keeper_only=True)]
    assert "consultar_reloj_frente" in publicas
    assert "consultar_secreto_npc" not in publicas
    assert "consultar_secreto_npc" in todas
