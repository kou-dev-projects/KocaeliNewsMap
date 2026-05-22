import pytest
from app.services.classifier import build_classifier_service
from app.services.classifier.config import ClassifierConfig
from app.services.classifier.factory import build_classifier_service as build_service_from_factory
from app.services.classifier.service import ClassifierService
from app.services.classifier.resolver import ConflictResolver
from app.services.classifier.schemas import (
    ClassificationInput, ClassificationResult, NewsCategory
)


@pytest.fixture
def svc():
    return build_classifier_service()   # mock mod — embedding yok


def test_yangin_classified(svc):
    r = svc.classify(ClassificationInput(
        title="Gebze'de fabrika yangını",
        content="İtfaiye ekipleri olay yerine sevk edildi. Duman yükseliyor."
    ))
    assert r.category == NewsCategory.YANGIN


def test_trafik_classified(svc):
    r = svc.classify(ClassificationInput(
        title="D100'de zincirleme kaza 3 yaralı"
    ))
    assert r.category == NewsCategory.TRAFIK_KAZASI


def test_elektrik_classified(svc):
    r = svc.classify(ClassificationInput(
        title="KKEDAŞ'tan kesinti uyarısı",
        summary="İzmit'te elektrik kesintisi yaşanacak"
    ))
    assert r.category == NewsCategory.ELEKTRIK_KESINTISI


def test_unknown_returns_unknown_or_closest(svc):
    r = svc.classify(ClassificationInput(title="Kocaeli'de yeni köprü açıldı"))
    assert r.category in NewsCategory.__members__.values()
    assert r.confidence >= 0.0


def test_result_has_method(svc):
    r = svc.classify(ClassificationInput(title="Yangın çıktı"))
    assert r.method in (
        "keyword", "semantic", "semantic_mock",
        "resolver_agree", "resolver_keyword", "resolver_priority",
        "keyword_only", "keyword_fallback_semantic_error", "semantic_error_unknown",
    )


def test_news_id_propagated(svc):
    r = svc.classify(ClassificationInput(
        title="Test haberi", news_id="haber_001"
    ))
    assert r.news_id == "haber_001"


def test_all_5_categories_classifiable(svc):
    cases = [
        ("Trafik kazası D100'de 2 araç çarpıştı yaralı var", NewsCategory.TRAFIK_KAZASI),
        ("Yangın itfaiye müdahale etti duman yükseliyor", NewsCategory.YANGIN),
        ("Hırsız suçüstü yakalandı gözaltına alındı", NewsCategory.HIRSIZLIK),
        ("Elektrik kesintisi KKEDAŞ trafo arızası", NewsCategory.ELEKTRIK_KESINTISI),
        ("Festival konser tiyatro etkinlik kutlama", NewsCategory.KULTUREL_ETKINLIK),
    ]
    for title, expected in cases:
        r = svc.classify(ClassificationInput(title=title))
        assert r.category == expected, f"'{title}' → beklenen {expected}, gelen {r.category}"


class _StubKeywordClassifier:
    def __init__(self, result):
        self._result = result

    def classify(self, input_data):
        return self._result


class _StubSemanticClassifier:
    def __init__(self, result):
        self._result = result
        self.calls = 0

    def classify(self, input_data):
        self.calls += 1
        return self._result


class _FailingSemanticClassifier:
    def classify(self, input_data):
        raise RuntimeError("semantic backend unavailable")


class _StubResolver:
    def resolve(self, keyword_result, semantic_result):
        return semantic_result


def test_semantic_disabled_skips_semantic_stage():
    """semantic_enabled=False olunca semantic classifier hiç çağrılmamalı."""
    keyword_result = ClassificationResult(
        category=NewsCategory.YANGIN,
        confidence=0.55,  # dynamic confidence artık 0.55
        method="keyword",
    )
    semantic_result = ClassificationResult(
        category=NewsCategory.HIRSIZLIK,
        confidence=0.9,
        method="semantic",
    )
    semantic = _StubSemanticClassifier(semantic_result)
    service = ClassifierService(
        keyword_classifier=_StubKeywordClassifier(keyword_result),
        semantic_classifier=semantic,
        resolver=_StubResolver(),
        semantic_enabled=False,
    )

    result = service.classify(ClassificationInput(title="test"))

    assert result.category == NewsCategory.YANGIN
    assert semantic.calls == 0  # semantic devre dışı


def test_semantic_always_runs_when_enabled():
    """semantic_enabled=True olunca keyword eşleşme olsa bile semantic çalışmalı."""
    keyword_result = ClassificationResult(
        category=NewsCategory.YANGIN,
        confidence=0.55,
        method="keyword",
    )
    semantic_result = ClassificationResult(
        category=NewsCategory.YANGIN,
        confidence=0.80,
        method="semantic",
    )
    semantic = _StubSemanticClassifier(semantic_result)
    service = ClassifierService(
        keyword_classifier=_StubKeywordClassifier(keyword_result),
        semantic_classifier=semantic,
        resolver=ConflictResolver(),
        semantic_enabled=True,
        keyword_only_mode=False,
    )

    result = service.classify(ClassificationInput(title="test"))

    # Semantic her zaman çalıştı — confidence == 1.0 bypass kaldırıldı
    assert semantic.calls == 1
    assert result.category == NewsCategory.YANGIN


def test_keyword_only_without_keyword_match_returns_unknown():
    semantic_result = ClassificationResult(
        category=NewsCategory.HIRSIZLIK,
        confidence=0.9,
        method="semantic",
    )
    semantic = _StubSemanticClassifier(semantic_result)
    service = ClassifierService(
        keyword_classifier=_StubKeywordClassifier(None),
        semantic_classifier=semantic,
        resolver=_StubResolver(),
        keyword_only_mode=True,
    )

    result = service.classify(ClassificationInput(title="test"))

    assert result.category == NewsCategory.UNKNOWN
    assert result.method == "keyword_only"
    assert semantic.calls == 0


def test_resolver_allows_semantic_unknown_to_override_weak_keyword():
    keyword_result = ClassificationResult(
        category=NewsCategory.KULTUREL_ETKINLIK,
        confidence=0.45,
        method="keyword",
    )
    semantic_result = ClassificationResult(
        category=NewsCategory.UNKNOWN,
        confidence=0.72,
        method="semantic",
    )
    service = ClassifierService(
        keyword_classifier=_StubKeywordClassifier(keyword_result),
        semantic_classifier=_StubSemanticClassifier(semantic_result),
        resolver=ConflictResolver(),
        semantic_enabled=True,
        keyword_only_mode=False,
    )

    result = service.classify(ClassificationInput(title="Kocaelispor kart projesi"))

    assert result.category == NewsCategory.UNKNOWN
    assert result.method == "resolver_semantic_unknown"


def test_factory_builds_embedding_service_when_semantic_is_enabled(monkeypatch):
    sentinel_embedding = object()

    monkeypatch.setattr(
        "app.services.classifier.factory.load_classifier_config",
        lambda: ClassifierConfig(
            semantic_enabled=True,
            semantic_confidence_threshold=0.42,
            semantic_margin_threshold=0.08,
            keyword_only_mode=False,
        ),
    )
    monkeypatch.setattr(
        "app.services.classifier.factory.build_embedding_service",
        lambda: sentinel_embedding,
    )

    service = build_service_from_factory()

    assert service._semantic_enabled is True
    assert service._semantic._embedding_service is sentinel_embedding


def test_semantic_failure_falls_back_to_keyword_result():
    keyword_result = ClassificationResult(
        category=NewsCategory.HIRSIZLIK,
        confidence=0.66,
        method="keyword",
        matched_keywords=["dolandirildi"],
        all_scores={"hirsizlik": 0.66},
    )
    service = ClassifierService(
        keyword_classifier=_StubKeywordClassifier(keyword_result),
        semantic_classifier=_FailingSemanticClassifier(),
        resolver=ConflictResolver(),
        semantic_enabled=True,
        keyword_only_mode=False,
    )

    result = service.classify(ClassificationInput(title="3 milyon TL dolandirildi"))

    assert result.category == NewsCategory.HIRSIZLIK
    assert result.method == "keyword_fallback_semantic_error"
    assert result.matched_keywords == ["dolandirildi"]


def test_semantic_failure_without_keyword_returns_unknown():
    service = ClassifierService(
        keyword_classifier=_StubKeywordClassifier(None),
        semantic_classifier=_FailingSemanticClassifier(),
        resolver=ConflictResolver(),
        semantic_enabled=True,
        keyword_only_mode=False,
    )

    result = service.classify(ClassificationInput(title="belirsiz haber"))

    assert result.category == NewsCategory.UNKNOWN
    assert result.method == "semantic_error_unknown"
