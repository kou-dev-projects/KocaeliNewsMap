from dataclasses import dataclass

from app.settings import settings


@dataclass(frozen=True)
class SchedulerConfig:
    enabled: bool
    timezone: str
    interval_hours: int
    lookback_days: int
    max_urls_per_source: int
    skipped_domains: tuple[str, ...] = ()


def _parse_skip_domains(value: str) -> tuple[str, ...]:
    if not value:
        return ()

    domains: list[str] = []
    for raw_domain in value.split(","):
        domain = raw_domain.strip().lower()
        if domain and domain not in domains:
            domains.append(domain)

    return tuple(domains)


def load_scheduler_config() -> SchedulerConfig:
    return SchedulerConfig(
        enabled=settings.scheduler_enabled,
        timezone=settings.scheduler_timezone,
        interval_hours=settings.scheduler_interval_hours,
        lookback_days=settings.scheduler_lookback_days,
        max_urls_per_source=settings.scheduler_max_urls_per_source,
        skipped_domains=_parse_skip_domains(settings.scheduler_skip_domains),
    )
