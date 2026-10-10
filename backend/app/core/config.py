"""Environment-backed configuration without embedding deployment secrets."""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    environment: str
    database_url: str | None

    @property
    def is_production(self) -> bool:
        return self.environment.lower() == "production"


def get_settings() -> Settings:
    database_url = os.getenv("DATABASE_URL", "").strip()
    return Settings(
        environment=os.getenv("ENVIRONMENT", "development"),
        database_url=database_url or None,
    )
