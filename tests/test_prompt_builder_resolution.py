"""Test de integración: PromptBuilder.load_system() valida `resolution:`
sin frenar el turno en curso (Fase 10)."""

from narrator.core.prompt_builder import PromptBuilder


def test_load_system_con_resolution_invalida_no_lanza(tmp_path, caplog):
    (tmp_path / "roto.yaml").write_text(
        'llm_system_prompt: "Sos un narrador."\n'
        "resolution:\n"
        '  mecanica: "d20_vs_dc"\n'
        "  # faltan dificultades/atributo_default/acciones a propósito\n",
        encoding="utf-8",
    )
    builder = PromptBuilder(systems_path=str(tmp_path))

    data = builder.load_system("roto")  # no debe lanzar

    assert data["resolution"]["mecanica"] == "d20_vs_dc"
    assert any("resolution inválida" in rec.message for rec in caplog.records)


def test_load_system_con_resolution_valida_no_loguea_error(tmp_path, caplog):
    (tmp_path / "ok.yaml").write_text(
        'llm_system_prompt: "Sos un narrador."\n'
        "resolution:\n"
        '  mecanica: "ratio"\n'
        "  bandas: {exito: 0.8, parcial: 0.5}\n",
        encoding="utf-8",
    )
    builder = PromptBuilder(systems_path=str(tmp_path))

    builder.load_system("ok")

    assert not any("resolution inválida" in rec.message for rec in caplog.records)


def test_load_system_sin_bloque_resolution_no_valida_nada(tmp_path, caplog):
    (tmp_path / "sin_resolution.yaml").write_text(
        'llm_system_prompt: "Sos un narrador."\n', encoding="utf-8"
    )
    builder = PromptBuilder(systems_path=str(tmp_path))

    data = builder.load_system("sin_resolution")  # no debe lanzar

    assert "resolution" not in data
    assert not any("resolution inválida" in rec.message for rec in caplog.records)
