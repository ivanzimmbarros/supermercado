"""Runner do job de recorrentes — agenda lida da base via ScheduleService."""

from __future__ import annotations

import argparse
import json
from datetime import datetime
from zoneinfo import ZoneInfo

from supermercado.bootstrap import bootstrap
from supermercado.persistence.db import create_db_engine, session_scope
from supermercado.services.config_service import ConfigService, ScheduleService
from supermercado.services.geo_service import GeoContextService


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

        result = {
            "should_run": decision_should,
            "reason": reason,
            "local_now": decision.local_now.isoformat(),
            "geo_context_id": geo.id,
            "postal_code": geo.postal_code,
            "schedule": decision.schedule.model_dump(),
        }

        if not decision_should:
            schedule_svc.register_job_run(
                "recurring_collect",
                geo.id,
                status="skipped",
                details=result,
            )
            return result

        # Coleta real será ligada quando os providers estiverem activos.
        # Nesta fase, apenas regista a execução e marca o slot.
        schedule_svc.mark_ran(decision.local_now, decision.schedule)
        schedule_svc.register_job_run(
            "recurring_collect",
            geo.id,
            status="ok_stub",
            details={
                **result,
                "note": "Providers ainda não ligados; slot marcado com sucesso.",
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
