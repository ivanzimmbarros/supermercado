"""Normalização de quantidades e preço por unidade canónica."""

from __future__ import annotations

import re
from dataclasses import dataclass


_UNIT_TO_CANON = {
    "ml": ("l", 0.001),
    "l": ("l", 1.0),
    "lt": ("l", 1.0),
    "ltr": ("l", 1.0),
    "cl": ("l", 0.01),
    "g": ("kg", 0.001),
    "gr": ("kg", 0.001),
    "kg": ("kg", 1.0),
    "un": ("un", 1.0),
    "uni": ("un", 1.0),
    "unidade": ("un", 1.0),
    "unidades": ("un", 1.0),
}


@dataclass(frozen=True)
class NormalizedQuantity:
    amount: float
    basis: str  # l | kg | un
    pack_count: int


@dataclass(frozen=True)
class UnitPrice:
    unit_price_final: float
    unit_basis: str
    normalized_amount: float


def normalize_unit(unit: str | None) -> str | None:
    if not unit:
        return None
    key = unit.strip().lower().replace(".", "")
    mapped = _UNIT_TO_CANON.get(key)
    return mapped[0] if mapped else key


def to_canonical_amount(
    quantity_value: float | None,
    quantity_unit: str | None,
    pack_count: int = 1,
) -> NormalizedQuantity | None:
    if quantity_value is None or quantity_value <= 0:
        return None
    if not quantity_unit:
        return None
    key = quantity_unit.strip().lower().replace(".", "")
    mapped = _UNIT_TO_CANON.get(key)
    if not mapped:
        return None
    basis, factor = mapped
    packs = pack_count if pack_count and pack_count > 0 else 1
    return NormalizedQuantity(amount=quantity_value * factor * packs, basis=basis, pack_count=packs)


def compute_unit_price(
    price_final: float,
    quantity_value: float | None,
    quantity_unit: str | None,
    pack_count: int = 1,
) -> UnitPrice | None:
    if price_final is None or price_final < 0:
        return None
    qty = to_canonical_amount(quantity_value, quantity_unit, pack_count)
    if qty is None or qty.amount <= 0:
        # fallback: tratar como 1 unidade
        return UnitPrice(unit_price_final=float(price_final), unit_basis="un", normalized_amount=1.0)
    return UnitPrice(
        unit_price_final=float(price_final) / qty.amount,
        unit_basis=qty.basis,
        normalized_amount=qty.amount,
    )


_QTY_RE = re.compile(
    r"(?P<pack>\d+\s*[x×]\s*)?(?P<value>\d+[.,]?\d*)\s*(?P<unit>ml|cl|l|lt|ltr|g|gr|kg|un|uni|unidades)\b",
    re.IGNORECASE,
)


def parse_quantity_from_text(text: str | None) -> tuple[float | None, str | None, int]:
    """Extrai (valor, unidade, pack_count) de textos tipo '1 L | 0,86 €/L' ou 'Pack 4x200 ml'."""
    if not text:
        return None, None, 1
    pack_count = 1
    pack_match = re.search(r"(\d+)\s*[x×]\s*(\d+[.,]?\d*)\s*(ml|cl|l|lt|g|kg)", text, re.I)
    if pack_match:
        pack_count = int(pack_match.group(1))
        value = float(pack_match.group(2).replace(",", "."))
        return value, pack_match.group(3).lower(), pack_count

    m = _QTY_RE.search(text)
    if not m:
        return None, None, 1
    value = float(m.group("value").replace(",", "."))
    unit = m.group("unit").lower()
    return value, unit, pack_count
