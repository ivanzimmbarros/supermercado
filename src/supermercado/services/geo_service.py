from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.orm import Session

from supermercado.defaults_seed import SEED_DISTRICT, SEED_LOCALITY, SEED_POSTAL_CODE
from supermercado.persistence.models import GeoContext, PriceSnapshot


class GeoContextService:
    """Gestão de códigos postais activos/congelados e continuidade histórica."""

    def __init__(self, session: Session):
        self.session = session

    def ensure_seeded(self) -> GeoContext:
        active = self.get_active()
        if active:
            return active
        existing = self.get_by_postal_code(SEED_POSTAL_CODE)
        if existing:
            return self.activate(SEED_POSTAL_CODE)
        return self.activate(
            SEED_POSTAL_CODE,
            locality=SEED_LOCALITY,
            district=SEED_DISTRICT,
        )

    def get_active(self) -> GeoContext | None:
        stmt = select(GeoContext).where(GeoContext.status == "active")
        return self.session.scalars(stmt).first()

    def get_by_postal_code(self, postal_code: str) -> GeoContext | None:
        normalized = self._normalize_postal(postal_code)
        stmt = select(GeoContext).where(GeoContext.postal_code == normalized)
        return self.session.scalars(stmt).first()

    def list_all(self) -> list[GeoContext]:
        stmt = select(GeoContext).order_by(GeoContext.postal_code.asc())
        return list(self.session.scalars(stmt))

    def activate(
        self,
        postal_code: str,
        locality: str | None = None,
        district: str | None = None,
        notes: str | None = None,
    ) -> GeoContext:
        """Activa um CP: congela o actual, cria ou reabre o alvo (histórico intacto)."""
        normalized = self._normalize_postal(postal_code)
        now = datetime.now(tz=ZoneInfo("UTC"))

        current = self.get_active()
        if current and current.postal_code == normalized:
            if locality:
                current.locality = locality
            if district:
                current.district = district
            if notes is not None:
                current.notes = notes
            self.session.flush()
            return current

        if current:
            current.status = "frozen"
            current.deactivated_at = now
            self.session.flush()

        target = self.get_by_postal_code(normalized)
        if target is None:
            target = GeoContext(
                postal_code=normalized,
                locality=locality,
                district=district,
                status="active",
                activated_at=now,
                deactivated_at=None,
                notes=notes,
            )
            self.session.add(target)
        else:
            target.status = "active"
            target.activated_at = now
            target.deactivated_at = None
            if locality:
                target.locality = locality
            if district:
                target.district = district
            if notes is not None:
                target.notes = notes

        self.session.flush()
        return target

    def count_snapshots(self, geo_context_id: str) -> int:
        stmt = select(PriceSnapshot).where(PriceSnapshot.geo_context_id == geo_context_id)
        return len(list(self.session.scalars(stmt)))

    @staticmethod
    def _normalize_postal(postal_code: str) -> str:
        cleaned = postal_code.strip().upper().replace(" ", "")
        if len(cleaned) == 7 and cleaned[4] != "-":
            cleaned = f"{cleaned[:4]}-{cleaned[4:]}"
        if len(cleaned) != 8 or cleaned[4] != "-":
            raise ValueError("Código postal inválido. Use o formato NNNN-NNN.")
        return cleaned
