"""Runner do job de recorrentes — agenda lida da base via ScheduleService."""

from __future__ import annotations

import argparse
import json
from datetime import datetime
from zoneinfo import ZoneInfo

from sqlalchemy import select

from supermercado.bootstrap import bootstrap
from supermercado.matching.engine import ProductRef
from supermercado.persistence.db import create_db_engine, session_scope
from supermercado.persistence.models import Product, RecurringProduct
from supermercado.services.config_service import ConfigService, ScheduleService
from supermercado.services.geo_service import GeoContextService
from supermercado.services.search_service import SearchService


def run_once(force: bool = False) -> dict:
    bootstrap()
    engine = create_db_engine()
    with session_scope(engine) as session:
        config = ConfigService(session)
        schedule_svc = ScheduleService(session, config)
        geo_svc = GeoContextService(session)
        geo = geo_svc.ensure_seeded()

        decision = schedule_svc.should_run_now()
        if force:
            decision_should = True
            reason = "forçado via --force"
        else:
            decision_should = decision.should_run
            reason = decision.reason

        result: dict = {
            "should_run": decision_should,
            "reason": reason,
            "local_now": decision.local_now.isoformat(),
            "geo_context_id": geo.id,
            "postal_code": geo.postal_code,
            "schedule": decision.schedule.model_dump(),
            "products_checked": 0,
            "errors": {},
        }

        if not decision_should:
            schedule_svc.register_job_run(
                "recurring_collect",
                geo.id,
                status="skipped",
                details=result,
            )
            return result

        search = SearchService(session)
        recurring = list(
            session.scalars(select(RecurringProduct).where(RecurringProduct.enabled.is_(True)))
        )
        for item in recurring:
            product = session.get(Product, item.product_id)
            if not product:
                continue
            try:
                search.search(
                    text=product.name,
                    ean=product.ean,
                    canonical=ProductRef(
                        name=product.name,
                        brand=product.brand,
                        ean=product.ean,
                        quantity_value=product.quantity_value,
                        quantity_unit=product.quantity_unit,
                        pack_count=product.pack_count or 1,
                        attributes=product.attributes_json,
                    ),
                    persist=True,
                )
                item.last_checked_at = datetime.now(tz=ZoneInfo("UTC"))
                result["products_checked"] += 1
            except Exception as exc:  # noqa: BLE001
                result["errors"][product.id] = str(exc)

        schedule_svc.mark_ran(decision.local_now, decision.schedule)
        schedule_svc.register_job_run(
            "recurring_collect",
            geo.id,
            status="ok" if not result["errors"] else "partial",
            details={
                **result,
                "finished_at_utc": datetime.now(tz=ZoneInfo("UTC")).isoformat(),
            },
        )
        result["executed"] = True
        return result


def main() -> None:
    parser = argparse.ArgumentParser(description="Job de produtos recorrentes")
    parser.add_argument(
        "--force",
        action="store_true",
        help="Ignora a janela/dias (útil para testes manuais)",
    )
    args = parser.parse_args()
    print(json.dumps(run_once(force=args.force), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
