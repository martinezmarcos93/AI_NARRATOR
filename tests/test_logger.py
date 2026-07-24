"""Test de regresión: logging con emoji no debe crashear en consolas de
encoding limitado (cp1252, típico en Windows) — descubierto verificando
la Fase 8 (metadata de NPC con íconos 🔴🟡🟢⚪)."""

import io

from narrator.logger import setup_logger


def test_logger_no_crashea_con_emoji_en_stream_cp1252(monkeypatch):
    # Simula una consola Windows real en cp1252: sin errors="replace" en
    # logger.py, este logging lanzaba UnicodeEncodeError y tumbaba el proceso.
    stream = io.TextIOWrapper(io.BytesIO(), encoding="cp1252")
    monkeypatch.setattr("sys.stdout", stream)

    logger = setup_logger(name="test_logger_regresion_emoji")
    logger.error("Prueba: 🔴 🟡 🟢 💡 ⚖ 🎲 y acentos: ó á é í ú ñ")  # no debe lanzar
