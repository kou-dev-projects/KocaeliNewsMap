from app.scripts.evaluate_live_location_logic import (
    CURATED_FIXTURE,
    _load_curated_samples,
)
from app.scripts.evaluate_location_logic import (
    EmptyNERProvider,
    VariantSpec,
    _predict_variant_districts,
)
from app.services.ner.service import NERService


def test_curated_live_fixture_loads_with_review_metadata():
    samples, metadata = _load_curated_samples(CURATED_FIXTURE)

    assert metadata["version"] == "labeled-live-2026-04-03.2"
    assert len(samples) == 6
    assert all(sample.expected for sample in samples)


def test_seed_rules_combined_matches_curated_live_fixture():
    variant = VariantSpec(
        name="seed_rules_combined",
        service=NERService(provider=EmptyNERProvider(), min_score=0.5),
        use_gazetteer=True,
        use_heuristic=True,
        use_provider=False,
    )
    samples, _ = _load_curated_samples(CURATED_FIXTURE)

    mismatches = []
    for sample in samples:
        predicted = _predict_variant_districts(
            variant=variant,
            title=sample.title,
            content=sample.content,
        )
        if predicted != sample.expected:
            mismatches.append((sample.sample_id, predicted, sample.expected))

    assert mismatches == []
