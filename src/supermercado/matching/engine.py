"""Matching idêntico / similar entre produto canónico e ofertas de mercado."""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass

from supermercado.normalization.units import to_canonical_amount


def _strip_accents(text: str) -> str:
    return "".join(
        c for c in unicodedata.normalize("NFKD", text) if not unicodedata.combining(c)
    )


def tokenize(text: str | None) -> set[str]:
    if not text:
        return set()
    cleaned = _strip_accents(text.lower())
    cleaned = re.sub(r"[^a-z0-9\s]", " ", cleaned)
    stop = {"de", "da", "do", "das", "dos", "e", "com", "sem", "emb", "pack"}
    return {t for t in cleaned.split() if len(t) > 1 and t not in stop}


@dataclass(frozen=True)
class MatchCandidate:
    match_type: str  # identical | similar | weak
    confidence: float
    unit_factor: float
    reason: str


@dataclass(frozen=True)
class ProductRef:
    name: str
    brand: str | None = None
    ean: str | None = None
    quantity_value: float | None = None
    quantity_unit: str | None = None
    pack_count: int = 1
    attributes: dict | None = None


def score_match(canonical: ProductRef, offer: ProductRef) -> MatchCandidate:
    if canonical.ean and offer.ean and canonical.ean == offer.ean:
        return MatchCandidate("identical", 1.0, 1.0, "EAN idêntico")

    brand_score = 0.0
    if canonical.brand and offer.brand:
        cb = _strip_accents(canonical.brand.lower())
        ob = _strip_accents(offer.brand.lower())
        if cb == ob:
            brand_score = 1.0
        elif cb in ob or ob in cb:
            brand_score = 0.7
        # marcas próprias: Pingo Doce ↔ Continente → não idêntico de marca
    elif not canonical.brand and not offer.brand:
        brand_score = 0.4

    tokens_a = tokenize(canonical.name)
    tokens_b = tokenize(offer.name)
    if tokens_a and tokens_b:
        overlap = len(tokens_a & tokens_b) / max(len(tokens_a | tokens_b), 1)
    else:
        overlap = 0.0

    attr_bonus = 0.0
    attrs = canonical.attributes or {}
    offer_name = _strip_accents((offer.name or "").lower())
    for key, val in attrs.items():
        if val is True and key.replace("_", " ") in offer_name:
            attr_bonus += 0.05
        elif isinstance(val, str) and _strip_accents(val.lower()) in offer_name:
            attr_bonus += 0.05
    attr_bonus = min(attr_bonus, 0.2)

    unit_factor = 1.0
    qty_score = 0.5
    ca = to_canonical_amount(canonical.quantity_value, canonical.quantity_unit, canonical.pack_count)
    oa = to_canonical_amount(offer.quantity_value, offer.quantity_unit, offer.pack_count)
    if ca and oa and ca.basis == oa.basis and ca.amount > 0 and oa.amount > 0:
        ratio = oa.amount / ca.amount
        unit_factor = ratio
        if abs(ratio - 1.0) < 0.05:
            qty_score = 1.0
        elif 0.4 <= ratio <= 2.6:
            qty_score = 0.7  # similar por volume (ex. 250 vs 500)
        else:
            qty_score = 0.3

    confidence = min(1.0, 0.45 * overlap + 0.35 * brand_score + 0.20 * qty_score + attr_bonus)

    if confidence >= 0.85 and abs(unit_factor - 1.0) < 0.05 and brand_score >= 0.7:
        return MatchCandidate("identical", confidence, 1.0, "nome/marca/quantidade alinhados")
    if confidence >= 0.55:
        return MatchCandidate(
            "similar",
            confidence,
            unit_factor,
            "similaridade por natureza/atributos/volume",
        )
    return MatchCandidate("weak", confidence, unit_factor, "confiança insuficiente")
