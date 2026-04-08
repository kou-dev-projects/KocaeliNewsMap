from app.services.classifier.schemas import ClassificationInput, NewsCategory
from app.services.classifier.semantic_classifier import SemanticClassifier
from app.services.embedding.schemas import TextEmbedding


class StubEmbeddingService:
    def __init__(self, mapping: dict[str, list[float]]):
        self._mapping = mapping

    def embed(self, input_data):
        text = input_data.build_text_payload()
        vector = self._mapping[text]
        return TextEmbedding(
            vector=vector,
            dimension=len(vector),
            provider="stub",
        )


def test_semantic_classifier_returns_best_matching_category():
    exemplars = {
        NewsCategory.TRAFIK_KAZASI: ("trafik_ornek",),
        NewsCategory.YANGIN: ("yangin_ornek",),
        NewsCategory.UNKNOWN: ("unknown_ornek",),
    }
    mapping = {
        "trafik_kazasi_0\ntrafik_ornek": [1.0, 0.0, 0.0],
        "yangin_0\nyangin_ornek": [0.0, 1.0, 0.0],
        "unknown_0\nunknown_ornek": [0.0, 0.0, 1.0],
        "D-100'de zincirleme trafik kazasi\nAraclar carpisarak yolu kapatti.": [0.95, 0.05, 0.0],
    }
    classifier = SemanticClassifier(
        embedding_service=StubEmbeddingService(mapping),
        threshold=0.30,
        margin_threshold=0.05,
        exemplar_catalog=exemplars,
    )

    result = classifier.classify(
        ClassificationInput(
            title="D-100'de zincirleme trafik kazasi",
            content="Araclar carpisarak yolu kapatti.",
        )
    )

    assert result.category == NewsCategory.TRAFIK_KAZASI
    assert result.method == "semantic"


def test_semantic_classifier_returns_unknown_when_margin_is_too_small():
    exemplars = {
        NewsCategory.KULTUREL_ETKINLIK: ("etkinlik_ornek",),
        NewsCategory.UNKNOWN: ("unknown_ornek",),
    }
    mapping = {
        "kulturel_etkinlik_0\netkinlik_ornek": [1.0, 0.0],
        "unknown_0\nunknown_ornek": [0.88, 0.12],
        "Kocaelispor kart projesi\nKulup yeni gelir modeli icin banka ile gorusuyor.": [0.90, 0.10],
    }
    classifier = SemanticClassifier(
        embedding_service=StubEmbeddingService(mapping),
        threshold=0.30,
        margin_threshold=0.08,
        exemplar_catalog=exemplars,
    )

    result = classifier.classify(
        ClassificationInput(
            title="Kocaelispor kart projesi",
            content="Kulup yeni gelir modeli icin banka ile gorusuyor.",
        )
    )

    assert result.category == NewsCategory.UNKNOWN


def test_semantic_classifier_returns_unknown_when_score_is_below_threshold():
    exemplars = {
        NewsCategory.HIRSIZLIK: ("hirsizlik_ornek",),
        NewsCategory.UNKNOWN: ("unknown_ornek",),
    }
    mapping = {
        "hirsizlik_0\nhirsizlik_ornek": [1.0, 0.0],
        "unknown_0\nunknown_ornek": [0.0, 1.0],
        "Belediye meclisinde butce gorusuldu\nFaaliyet raporu tartisildi.": [0.3, 0.3],
    }
    classifier = SemanticClassifier(
        embedding_service=StubEmbeddingService(mapping),
        threshold=0.60,
        margin_threshold=0.05,
        exemplar_catalog=exemplars,
    )

    result = classifier.classify(
        ClassificationInput(
            title="Belediye meclisinde butce gorusuldu",
            content="Faaliyet raporu tartisildi.",
        )
    )

    assert result.category == NewsCategory.UNKNOWN
