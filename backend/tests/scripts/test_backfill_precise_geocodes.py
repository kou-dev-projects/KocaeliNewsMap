from app.pipelines.location_versions import (
    GAZETTEER_VERSION,
    LOCATION_PIPELINE_VERSION,
    LOGICAL_LOCATION_CATALOG_VERSION,
)
from app.scripts.backfill_precise_geocodes import _build_query
from app.services.geocoding.provider_versions import PROVIDER_VERSIONS


def test_stale_version_query_targets_missing_or_outdated_location_metadata():
    query = _build_query("stale-version")

    assert query == {
        "$or": [
            {"location_pipeline_version": {"$exists": False}},
            {"location_pipeline_version": {"$ne": LOCATION_PIPELINE_VERSION}},
            {"gazetteer_version": {"$exists": False}},
            {"gazetteer_version": {"$ne": GAZETTEER_VERSION}},
            {"logical_catalog_version": {"$exists": False}},
            {"logical_catalog_version": {"$ne": LOGICAL_LOCATION_CATALOG_VERSION}},
            {
                "geocode_provider": "mock",
                "geocode_provider_version": {"$exists": False},
            },
            {
                "geocode_provider": "mock",
                "geocode_provider_version": {"$ne": PROVIDER_VERSIONS["mock"]},
            },
            {
                "geocode_provider": "nominatim",
                "geocode_provider_version": {"$exists": False},
            },
            {
                "geocode_provider": "nominatim",
                "geocode_provider_version": {
                    "$ne": PROVIDER_VERSIONS["nominatim"]
                },
            },
            {
                "geocode_provider": "opencage",
                "geocode_provider_version": {"$exists": False},
            },
            {
                "geocode_provider": "opencage",
                "geocode_provider_version": {
                    "$ne": PROVIDER_VERSIONS["opencage"]
                },
            },
        ]
    }


def test_district_fallback_query_keeps_legacy_cleanup_mode():
    assert _build_query("district-fallback") == {
        "geocode_provider": "district_fallback",
        "geocode_point": {"$ne": None},
    }


def test_approximate_without_district_query_targets_stale_map_points():
    assert _build_query("approximate-without-district") == {
        "geocode_status": "approximate",
        "district_predicted": None,
        "geocode_point": {"$ne": None},
    }
