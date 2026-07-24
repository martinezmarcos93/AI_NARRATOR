"""Test Fase 21: tarjetas de personaje SillyTavern V2 (PNG + chunk tEXt "chara")."""

import struct
import zlib

from narrator.core.character_card import read_chara_chunk, write_chara_chunk


def _chunk(ctype: bytes, data: bytes) -> bytes:
    return struct.pack(">I", len(data)) + ctype + data + struct.pack(
        ">I", zlib.crc32(ctype + data) & 0xFFFFFFFF
    )


def _minimal_png() -> bytes:
    """PNG 1x1 RGB válido mínimo, generado a mano — no depende de Pillow."""
    ihdr = struct.pack(">IIBBBBB", 1, 1, 8, 2, 0, 0, 0)
    raw = b"\x00" + b"\xff\xff\xff"  # byte de filtro + 1 píxel RGB
    idat = zlib.compress(raw)
    return b"\x89PNG\r\n\x1a\n" + _chunk(b"IHDR", ihdr) + _chunk(b"IDAT", idat) + _chunk(b"IEND", b"")


def test_round_trip_exportar_importar():
    png = _minimal_png()
    personaje = {"nombre": "Kael el Mendigo", "rol": "informante", "amenaza": "baja"}
    png_con_chara = write_chara_chunk(png, personaje)
    assert read_chara_chunk(png_con_chara) == personaje


def test_png_original_sigue_siendo_valido_tras_escribir():
    png = _minimal_png()
    png_con_chara = write_chara_chunk(png, {"nombre": "X"})
    assert png_con_chara.startswith(b"\x89PNG\r\n\x1a\n")
    assert b"IEND" in png_con_chara


def test_read_sin_chunk_chara_devuelve_none():
    assert read_chara_chunk(_minimal_png()) is None


def test_read_no_es_png_devuelve_none():
    assert read_chara_chunk(b"esto no es un png") is None


def test_write_no_es_png_lanza_error():
    import pytest
    with pytest.raises(ValueError):
        write_chara_chunk(b"esto no es un png", {"nombre": "X"})


def test_con_acentos_y_caracteres_especiales():
    png = _minimal_png()
    personaje = {"nombre": "Ñoño Muñoz", "descripcion": "café, corazón, año"}
    png_con_chara = write_chara_chunk(png, personaje)
    assert read_chara_chunk(png_con_chara) == personaje
