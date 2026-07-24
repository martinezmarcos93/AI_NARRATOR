"""Tests de la cola de iniciativa — combate por turnos, Python puro."""

from narrator.core.initiative import InitiativeQueue


# ── orden por iniciativa descendente ────────────────────────────
def test_add_ordena_por_iniciativa_descendente():
    q = InitiativeQueue()
    q.add("Goblin", 8)
    q.add("Kael", 15)
    q.add("Mira", 12)
    assert q.order() == ["Kael", "Mira", "Goblin"]


def test_current_name_es_el_primero_al_iniciar():
    q = InitiativeQueue()
    q.add("Kael", 15)
    q.add("Goblin", 8)
    assert q.current_name() == "Kael"


# ── next_turn: rotación y ronda ──────────────────────────────────
def test_next_turn_avanza_en_orden():
    q = InitiativeQueue()
    q.add("Kael", 15)
    q.add("Mira", 12)
    q.add("Goblin", 8)
    assert q.next_turn() == "Mira"
    assert q.next_turn() == "Goblin"


def test_next_turn_da_la_vuelta_e_incrementa_ronda():
    q = InitiativeQueue()
    q.add("Kael", 15)
    q.add("Goblin", 8)
    assert q.round() == 1
    q.next_turn()  # -> Goblin
    q.next_turn()  # -> Kael, cierra la vuelta
    assert q.current_name() == "Kael"
    assert q.round() == 2


def test_next_turn_salta_combatientes_caidos():
    q = InitiativeQueue()
    q.add("Kael", 15)
    q.add("Mira", 12)
    q.add("Goblin", 8)
    q.set_active("Mira", False)
    assert q.next_turn() == "Goblin"  # saltea a Mira


def test_next_turn_nadie_activo_devuelve_none():
    q = InitiativeQueue()
    q.add("Kael", 15)
    q.set_active("Kael", False)
    assert q.next_turn() is None


def test_cola_vacia_next_turn_devuelve_none():
    assert InitiativeQueue().next_turn() is None


# ── remove ────────────────────────────────────────────────────
def test_remove_combatiente_antes_del_turno_actual_ajusta_indice():
    q = InitiativeQueue()
    q.add("Kael", 15)
    q.add("Mira", 12)
    q.add("Goblin", 8)
    q.next_turn()  # turno: Mira (index 1)
    q.remove("Kael")  # estaba antes del turno actual (index 0 < 1)
    assert q.current_name() == "Mira"  # el turno activo no debe cambiar


def test_remove_todos_resetea_indice():
    q = InitiativeQueue()
    q.add("Kael", 15)
    q.remove("Kael")
    assert q.order() == []
    assert q.current_name() is None


def test_add_reemplaza_si_ya_existia():
    q = InitiativeQueue()
    q.add("Kael", 10)
    q.add("Kael", 20)  # re-agregar con otra iniciativa, no duplica
    assert q.order() == ["Kael"]


# ── is_active / reset ────────────────────────────────────────────
def test_is_active():
    q = InitiativeQueue()
    assert q.is_active() is False
    q.add("Kael", 10)
    assert q.is_active() is True


def test_reset():
    q = InitiativeQueue()
    q.add("Kael", 10)
    q.next_turn()
    q.reset()
    assert q.order() == []
    assert q.round() == 1


# ── serialización ─────────────────────────────────────────────
def test_to_dict_from_dict_round_trip():
    q = InitiativeQueue()
    q.add("Kael", 15)
    q.add("Goblin", 8)
    q.next_turn()
    q.set_active("Goblin", False)

    data = q.to_dict()
    q2 = InitiativeQueue.from_dict(data)

    assert q2.order() == q.order()
    assert q2.current_name() == q.current_name()
    assert q2.round() == q.round()
    # Goblin (turno actual) quedó inactivo tras la serialización; el
    # siguiente turno debe saltarlo y volver a Kael, que sigue activo.
    assert q2.next_turn() == "Kael"


def test_from_dict_vacio():
    q = InitiativeQueue.from_dict({})
    assert q.order() == []
    assert q.round() == 1
