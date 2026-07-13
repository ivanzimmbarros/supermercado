"""Sementes iniciais apenas para first-boot.

Nenhum módulo de domínio deve importar estes valores directamente
para regras operacionais em runtime. Use ConfigService / GeoContextService.
"""

from __future__ import annotations

# Seed geográfico inicial (substituível na UI)
SEED_POSTAL_CODE = "4815-413"
SEED_LOCALITY = "Vizela"
SEED_DISTRICT = "Braga"

# Seed da agenda de recorrentes (substituível na UI)
SEED_SCHEDULE = {
    "enabled": True,
    "weekdays": ["tue", "fri"],
    "time": "07:00",
    "timezone": "Europe/Lisbon",
    "executions_per_week": 2,
}

# Seed de janelas de oportunidade (substituível na UI)
SEED_OPPORTUNITY_WINDOWS_DAYS = [15, 30, 60]

# Mercados iniciais habilitados (substituível na UI / tabela markets)
SEED_ENABLED_MARKETS = ["continente", "pingo_doce"]

WEEKDAY_LABELS_PT = {
    "mon": "Segunda",
    "tue": "Terça",
    "wed": "Quarta",
    "thu": "Quinta",
    "fri": "Sexta",
    "sat": "Sábado",
    "sun": "Domingo",
}

ALL_WEEKDAYS = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]
