"""Testes unitários do scanner EAN."""

from __future__ import annotations

from io import BytesIO

import pytest

from supermercado.scanning.ean import (
    decode_ean_from_bytes,
    ean_checksum_ok,
    normalize_digits,
    validate_ean,
)


def test_normalize_digits_strips_noise():
    assert normalize_digits(" 560-1312 508007 ") == "5601312508007"


def test_validate_ean13_ok():
    result = validate_ean("5601312508007")
    assert result.ok
    assert result.ean == "5601312508007"
    assert result.symbology == "EAN-13"


def test_validate_ean_bad_checksum():
    result = validate_ean("5601312508000")
    assert result.ok is False
    assert "controlo" in result.message.lower() or "checksum" in result.message.lower() or "inválido" in result.message.lower()


def test_ean_checksum_helper():
    assert ean_checksum_ok("5601312508007")
    assert not ean_checksum_ok("123")


def test_decode_roundtrip_generated_barcode():
    pytest.importorskip("barcode")
    pytest.importorskip("pyzbar")
    from barcode import EAN13
    from barcode.writer import ImageWriter

    buf = BytesIO()
    EAN13("560131250800", writer=ImageWriter()).write(buf)
    result = decode_ean_from_bytes(buf.getvalue())
    assert result.ok
    assert result.ean == "5601312508007"
