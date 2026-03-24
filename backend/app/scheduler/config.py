from dataclasses import dataclass

from app.settings import settings


@dataclass(frozen=True)
class SchedulerConfig:
    enabled: bool
    timezone: str
    interval_hours: int
    lookback_days: int
    max_urls_per_source: int


def load_scheduler_config() -> SchedulerConfig:
    return SchedulerConfig(
        enabled=settings.scheduler_enabled,
        timezone=settings.scheduler_timezone,
        interval_hours=settings.scheduler_interval_hours,
        lookback_days=settings.scheduler_lookback_days,
        max_urls_per_source=settings.scheduler_max_urls_per_source,
    )
