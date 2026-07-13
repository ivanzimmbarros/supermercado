from __future__ import annotations

from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

from sqlalchemy.orm import Session

from supermercado.defaults_seed import (
    SEED_ENABLED_MARKETS,
    SEED_OPPORTUNITY_WINDOWS_DAYS,
    SEED_SCHEDULE,
)
from supermercado.domain.schedule import RecurringScheduleConfig, ScheduleDecision
from supermercado.persistence.models import AppSetting, JobRun, SettingsAudit

SETTINGS_RECURRING = "recurring_schedule"
SETTINGS_WINDOWS = "opportunity_windows_days"
SETTINGS_ENABLED_MARKETS = "enabled_markets"
SETTINGS_LAST_RECURRING_RUN = "last_recurring_run"


class ConfigService:
    """Leitura/escrita de todas as definições operacionais (sem hardcode de runtime)."""

    def __init__(self, session: Session):
        self.session = session

    def ensure_seeded(self) -> None:
        if self._get_raw(SETTINGS_RECURRING) is None:
            self.set_setting(SETTINGS_RECURRING, dict(SEED_SCHEDULE), changed_by=None)
        if self._get_raw(SETTINGS_WINDOWS) is None:
            self.set_setting(
                SETTINGS_WINDOWS,
                {"days": list(SEED_OPPORTUNITY_WINDOWS_DAYS)},
                changed_by=None,
            )
        if self._get_raw(SETTINGS_ENABLED_MARKETS) is None:
            self.set_setting(
                SETTINGS_ENABLED_MARKETS,
                {"market_ids": list(SEED_ENABLED_MARKETS)},
                changed_by=None,
            )

    def _get_raw(self, key: str) -> dict[str, Any] | None:
        row = self.session.get(AppSetting, key)
        return None if row is None else dict(row.value_json)

    def get_setting(self, key: str) -> dict[str, Any]:
        self.ensure_seeded()
        value = self._get_raw(key)
        if value is None:
            raise KeyError(f"Setting em falta: {key}")
        return value

    def set_setting(
        self, key: str, value: dict[str, Any], changed_by: str | None = None
    ) -> None:
        old = self._get_raw(key)
        row = self.session.get(AppSetting, key)
        if row is None:
            row = AppSetting(key=key, value_json=value, updated_by=changed_by)
            self.session.add(row)
        else:
            row.value_json = value
            row.updated_by = changed_by
        self.session.add(
            SettingsAudit(
                key=key,
                old_value=old,
                new_value=value,
                changed_by=changed_by,
            )
        )
        self.session.flush()

    def get_recurring_schedule(self) -> RecurringScheduleConfig:
        payload = self.get_setting(SETTINGS_RECURRING)
        return RecurringScheduleConfig.model_validate(payload)

    def set_recurring_schedule(
        self, schedule: RecurringScheduleConfig, changed_by: str | None = None
    ) -> RecurringScheduleConfig:
        # Revalida invariantes
        validated = RecurringScheduleConfig.model_validate(schedule.model_dump())
        self.set_setting(SETTINGS_RECURRING, validated.to_settings_payload(), changed_by)
        return validated

    def get_opportunity_windows_days(self) -> list[int]:
        payload = self.get_setting(SETTINGS_WINDOWS)
        days = [int(d) for d in payload.get("days", [])]
        if not days:
            raise ValueError("opportunity_windows_days não pode ser vazio")
        return sorted(days)

    def set_opportunity_windows_days(
        self, days: list[int], changed_by: str | None = None
    ) -> list[int]:
        cleaned = sorted({int(d) for d in days if int(d) > 0})
        if not cleaned:
            raise ValueError("Informe pelo menos uma janela em dias")
        self.set_setting(SETTINGS_WINDOWS, {"days": cleaned}, changed_by)
        return cleaned

    def get_enabled_market_ids(self) -> list[str]:
        payload = self.get_setting(SETTINGS_ENABLED_MARKETS)
        return list(payload.get("market_ids", []))

    def set_enabled_market_ids(
        self, market_ids: list[str], changed_by: str | None = None
    ) -> list[str]:
        cleaned = [m.strip() for m in market_ids if m.strip()]
        self.set_setting(SETTINGS_ENABLED_MARKETS, {"market_ids": cleaned}, changed_by)
        return cleaned


class ScheduleService:
    """Decide se o job deve correr agora, com base apenas na config persistida."""

    def __init__(self, session: Session, config: ConfigService | None = None):
        self.session = session
        self.config = config or ConfigService(session)

    def should_run_now(
        self,
        now_utc: datetime | None = None,
        window_minutes: int = 15,
    ) -> ScheduleDecision:
        schedule = self.config.get_recurring_schedule()
        tz = ZoneInfo(schedule.timezone)
        now_utc = now_utc or datetime.now(tz=ZoneInfo("UTC"))
        if now_utc.tzinfo is None:
            now_utc = now_utc.replace(tzinfo=ZoneInfo("UTC"))
        local_now = now_utc.astimezone(tz)

        if not schedule.enabled:
            return ScheduleDecision(False, "agenda desativada", local_now, schedule)

        weekday = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"][local_now.weekday()]
        if weekday not in schedule.weekdays:
            return ScheduleDecision(
                False, f"hoje ({weekday}) não está na agenda", local_now, schedule
            )

        target = schedule.parsed_time()
        scheduled_dt = local_now.replace(
            hour=target.hour, minute=target.minute, second=0, microsecond=0
        )
        delta = abs((local_now - scheduled_dt).total_seconds()) / 60.0
        if delta > window_minutes:
            return ScheduleDecision(
                False,
                f"fora da janela horária ({schedule.time} ±{window_minutes} min)",
                local_now,
                schedule,
            )

        if self._already_ran_slot(schedule, local_now):
            return ScheduleDecision(
                False, "já executado neste slot", local_now, schedule
            )

        return ScheduleDecision(True, "slot válido", local_now, schedule)

    def _already_ran_slot(
        self, schedule: RecurringScheduleConfig, local_now: datetime
    ) -> bool:
        marker = self.config._get_raw(SETTINGS_LAST_RECURRING_RUN)
        if not marker:
            return False
        last_iso = marker.get("local_slot")
        if not last_iso:
            return False
        # Slot id = data local + hora configurada
        slot_id = f"{local_now.date().isoformat()}T{schedule.time}"
        return last_iso == slot_id

    def mark_ran(self, local_now: datetime, schedule: RecurringScheduleConfig) -> None:
        slot_id = f"{local_now.date().isoformat()}T{schedule.time}"
        self.config.set_setting(
            SETTINGS_LAST_RECURRING_RUN,
            {
                "local_slot": slot_id,
                "marked_at_utc": datetime.now(tz=ZoneInfo("UTC")).isoformat(),
            },
            changed_by=None,
        )

    def register_job_run(
        self,
        job_name: str,
        geo_context_id: str | None,
        status: str,
        details: dict[str, Any] | None = None,
    ) -> JobRun:
        run = JobRun(
            job_name=job_name,
            geo_context_id=geo_context_id,
            started_at=datetime.now(tz=ZoneInfo("UTC")),
            finished_at=datetime.now(tz=ZoneInfo("UTC")) if status != "running" else None,
            status=status,
            details_json=details,
        )
        self.session.add(run)
        self.session.flush()
        return run
