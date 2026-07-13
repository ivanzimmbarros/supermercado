"""Validação e leitura de códigos EAN (8/13) a partir de texto ou imagem."""

from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO
from typing import BinaryIO


@dataclass(frozen=True)
class ScanResult:
    ok: bool
    ean: str | None
    symbology: str | None
    message: str


def normalize_digits(raw: str | None) -> str:
    if not raw:
        return ""
    return "".join(ch for ch in raw.strip() if ch.isdigit())


def ean_checksum_ok(digits: str) -> bool:
    if len(digits) not in {8, 13}:
        return False
    body, check = digits[:-1], int(digits[-1])
    total = 0
    # pesos da direita para a esquerda: 3,1,3,1...
    for i, ch in enumerate(reversed(body)):
        weight = 3 if i % 2 == 0 else 1
        total += int(ch) * weight
    calc = (10 - (total % 10)) % 10
    return calc == check


def validate_ean(raw: str | None) -> ScanResult:
    digits = normalize_digits(raw)
    if not digits:
        return ScanResult(False, None, None, "Indique um código EAN.")
    if len(digits) not in {8, 13}:
        return ScanResult(
            False,
            digits,
            None,
            f"EAN deve ter 8 ou 13 dígitos (recebido: {len(digits)}).",
        )
    if not ean_checksum_ok(digits):
        return ScanResult(False, digits, f"EAN-{len(digits)}", "Dígito de controlo EAN inválido.")
    return ScanResult(True, digits, f"EAN-{len(digits)}", "EAN válido.")


def decode_ean_from_bytes(data: bytes) -> ScanResult:
    """Lê EAN de imagem (JPEG/PNG). Degrada com mensagem clara se deps falharem."""
    if not data:
        return ScanResult(False, None, None, "Imagem vazia.")
    try:
        from PIL import Image
        from pyzbar.pyzbar import decode
    except Exception as exc:  # noqa: BLE001
        return ScanResult(
            False,
            None,
            None,
            "Leitura por imagem indisponível neste ambiente "
            f"(instale pillow/pyzbar/libzbar). Detalhe: {exc}",
        )

    try:
        image = Image.open(BytesIO(data))
        if image.mode not in {"RGB", "L"}:
            image = image.convert("RGB")
        decoded = decode(image)
    except Exception as exc:  # noqa: BLE001
        return ScanResult(False, None, None, f"Não foi possível ler a imagem: {exc}")

    if not decoded:
        return ScanResult(
            False,
            None,
            None,
            "Nenhum código de barras encontrado. Tente outra foto ou introduza o EAN manualmente.",
        )

    # Preferir EAN/UPC
    preferred = []
    others = []
    for item in decoded:
        text = item.data.decode("utf-8", errors="ignore")
        sym = (item.type or "").upper()
        if sym in {"EAN13", "EAN8", "UPCA", "UPCE"}:
            preferred.append((text, sym))
        else:
            others.append((text, sym))

    for text, sym in preferred + others:
        digits = normalize_digits(text)
        # UPC-A 12 dígitos → prefixar 0 para EAN-13
        if len(digits) == 12:
            digits = "0" + digits
        result = validate_ean(digits)
        if result.ok:
            return ScanResult(True, result.ean, sym or result.symbology, "EAN lido da imagem.")
        # se checksum falhar mas tiver comprimento certo, ainda devolver com aviso
        if len(digits) in {8, 13}:
            return ScanResult(
                False,
                digits,
                sym,
                "Código lido mas checksum EAN inválido — confirme manualmente.",
            )

    raw = normalize_digits(decoded[0].data.decode("utf-8", errors="ignore"))
    return ScanResult(False, raw or None, decoded[0].type, "Código lido não é EAN válido.")


def decode_ean_from_upload(file_obj: BinaryIO | None) -> ScanResult:
    if file_obj is None:
        return ScanResult(False, None, None, "Sem ficheiro.")
    data = file_obj.read()
    if hasattr(file_obj, "seek"):
        try:
            file_obj.seek(0)
        except Exception:
            pass
    return decode_ean_from_bytes(data)
