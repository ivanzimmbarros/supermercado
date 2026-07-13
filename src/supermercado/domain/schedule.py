from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, time
from typing import Any
from zoneinfo import ZoneInfo

from pydantic import BaseModel, Field, field_validator, model_validator

from supermercado.defaults_seed import ALL_WEEKDAYS


class RecurringScheduleConfig(BaseModel):
    enabled: bool = True
    weekdays: list[str] = Field(default_factory=list)
    time: str = "07:00"
    timezone: str = "Europe/Lisbon"
    executions_per_week: int = Field(ge=0, le=7)

    @field_validator("weekdays")
    @classmethod
    def validate_weekdays(cls, values: list[str]) -> list[str]:
        normalized = [v.strip().lower() for v in values]
        unknown = [v for v in normalized if v not in ALL_WEEKDAYS]
        if unknown:
            raise ValueError(f"Dias inválidos: {unknown}")
        if len(set(normalized)) != len(normalized):
            raise ValueError("Dias da semana não podem repetir-se")
        return normalized

    @field_validator("time")
    @classmethod
    def validate_time(cls, value: str) -> str:
        parts = value.split(":")
        if len(parts) != 2:
            raise ValueError("Hora deve estar no formato HH:MM")
        hour, minute = int(parts[0]), int(parts[1])
        if not (0 <= hour <= 23 and 0 <= minute <= 59):
            raise ValueError("Hora fora do intervalo válido")
        return f"{hour:02d}:{minute:02d}"

    @model_validator(mode="after")
    def match_execution_count(self) -> RecurringScheduleConfig:
        if len(self.weekdays) != self.executions_per_week:
            raise ValueError(
                "executions_per_week deve ser igual ao número de dias selecionados "
                f"({len(self.weekdays)} dias ≠ {self.executions_per_week})"
            )
        # Validar timezone
        ZoneInfo(self.timezone)
        return self

    def parsed_time(self) -> time:
        hour, minute = map(int, self.time.split(":"))
        return time(hour=hour, minute=minute)

    def to_settings_payload(self) -> dict[str, Any]:
        return self.model_dump()


@dataclass(frozen=True)
class ScheduleDecision:
    should_run: bool
    reason: str
    local_now: datetime
    schedule: RecurringScheduleConfig
