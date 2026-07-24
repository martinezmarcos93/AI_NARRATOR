"""Test de integración: Orchestrator._get_known_entity_names (Fase 8, recall por mención)."""

from narrator.agents.orchestrator import Orchestrator


class _FakeRetriever:
    def __init__(self, npcs=None, locations=None):
        self._npcs = npcs or []
        self._locations = locations or []

    def get_by_type(self, tipo, max_files=50):
        if tipo == "npc":
            return self._npcs
        if tipo == "locacion":
            return self._locations
        return []


def _npc(nombre):
    return {"meta": {"tipo": "npc", "nombre": nombre}, "body": "", "path": f"{nombre}.md"}


def _loc(nombre):
    return {"meta": {"tipo": "locacion", "nombre": nombre}, "body": "", "path": f"{nombre}.md"}


class _Orq:
    """Réplica mínima del wiring del Orchestrator para _get_known_entity_names."""

    _get_known_entity_names = Orchestrator._get_known_entity_names

    def __init__(self, npcs=None, locations=None):
        self.retriever = _FakeRetriever(npcs, locations)


def test_junta_npcs_y_locaciones():
    orq = _Orq(npcs=[_npc("Kael"), _npc("Mira")], locations=[_loc("El Muelle Viejo")])
    assert orq._get_known_entity_names() == ["Kael", "Mira", "El Muelle Viejo"]


def test_ignora_entidades_sin_nombre():
    orq = _Orq(npcs=[{"meta": {"tipo": "npc"}, "body": "", "path": "x.md"}])
    assert orq._get_known_entity_names() == []


def test_vault_vacio_devuelve_lista_vacia():
    orq = _Orq()
    assert orq._get_known_entity_names() == []
