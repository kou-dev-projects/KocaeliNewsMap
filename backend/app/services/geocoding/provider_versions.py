from __future__ import annotations

PROVIDER_VERSIONS: dict[str, str] = {
    "mock": "mock@1.0",
    "nominatim": "nominatim@1.1",
    "opencage": "opencage@1.0",
}

PROVIDER_VERSION_CATALOG = ";".join(
    f"{provider}={version}"
    for provider, version in sorted(PROVIDER_VERSIONS.items())
)


def get_provider_version(provider: str | None) -> str | None:
    if provider is None:
        return None
    return PROVIDER_VERSIONS.get(provider)
