import pytest
from app.services.classifier.resolver import ConflictResolver
from app.services.classifier.schemas import (
    ClassificationResult, NewsCategory
)


@pytest.fixture
def resolver():
    return ConflictResolver()


def _make(cat, conf, method="keyword", keywords=None):
    return ClassificationResult(
        category=cat, confidence=conf, method=method,
        matched_keywords=keywords or [],
    )


def test_no_keyword_returns_semantic(resolver):
    sem = _make(NewsCategory.YANGIN, 0.85, "semantic")
    result = resolver.resolve(None, sem)
    assert result.category == NewsCategory.YANGIN
    assert result.method == "semantic"


def test_same_category_averages_confidence(resolver):
    kw = _make(NewsCategory.YANGIN, 1.0)
    sem = _make(NewsCategory.YANGIN, 0.80, "semantic")
    result = resolver.resolve(kw, sem)
    assert result.category == NewsCategory.YANGIN
    assert result.confidence == pytest.approx(0.90, abs=0.01)
    assert result.method == "resolver_agree"


def test_high_conf_keyword_wins(resolver):
    kw = _make(NewsCategory.TRAFIK_KAZASI, 1.0)
    sem = _make(NewsCategory.YANGIN, 0.70, "semantic")
    result = resolver.resolve(kw, sem)
    assert result.category == NewsCategory.TRAFIK_KAZASI
    assert result.method == "resolver_keyword"


def test_priority_trafik_over_yangin(resolver):
    # Confidence yakın → öncelik sırası devreye girer
    kw = _make(NewsCategory.TRAFIK_KAZASI, 0.80)
    sem = _make(NewsCategory.YANGIN, 0.79, "semantic")
    result = resolver.resolve(kw, sem)
    assert result.category == NewsCategory.TRAFIK_KAZASI
    assert result.method == "resolver_priority"


def test_all_5_categories_have_priority():
    from app.services.classifier.schemas import CATEGORY_PRIORITY
    for cat in NewsCategory:
        if cat != NewsCategory.UNKNOWN:
            assert cat in CATEGORY_PRIORITY