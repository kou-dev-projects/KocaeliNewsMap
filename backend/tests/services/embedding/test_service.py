from __future__ import annotations
import pytest
import numpy as np

from app.services.embedding import build_embedding_service
from app.services.embedding.factory import build_embedding_service as build_embedding_service_from_factory
from app.services.embedding.config import EmbeddingConfig
from app.services.embedding.schemas import EmbeddingInput


@pytest.fixture
def cfg() -> EmbeddingConfig:
    return EmbeddingConfig(
        text_provider="mock",
        text_dimension=1024,
        duplicate_threshold=0.90,
        text_score_weight=1.00,
        cost_log_path="/tmp/test_embedding_cost.jsonl",
    )


@pytest.fixture
def svc(cfg):
    return build_embedding_service(cfg)


# --- embed() testleri ---

def test_text_embedding_is_1024_dim(svc):
    text_emb = svc.embed(EmbeddingInput(title="Gebze yangın", source="test.com"))
    assert text_emb.dimension == 1024
    assert len(text_emb.vector) == 1024


def test_text_embedding_is_l2_normalized(svc):
    text_emb = svc.embed(EmbeddingInput(title="İzmit kaza", source="test.com"))
    norm = np.linalg.norm(text_emb.vector)
    assert abs(norm - 1.0) < 1e-5


def test_same_input_same_vector(svc):
    inp = EmbeddingInput(title="Aynı haber", source="a.com")
    t1 = svc.embed(inp)
    t2 = svc.embed(inp)
    assert t1.vector == t2.vector


def test_different_input_different_vector(svc):
    t1 = svc.embed(EmbeddingInput(title="Yangın haberi", source="a.com"))
    t2 = svc.embed(EmbeddingInput(title="Trafik kazası", source="b.com"))
    assert t1.vector != t2.vector


def test_provider_name_in_result(svc):
    text_emb = svc.embed(EmbeddingInput(title="Test", source="x.com"))
    assert text_emb.provider == "mock-text"


# --- decide_duplicate() testleri ---

def test_no_candidates_returns_not_duplicate(svc):
    text_emb = svc.embed(EmbeddingInput(title="Test", source="a.com"))
    result = svc.decide_duplicate(text_emb, [], "a.com")
    assert result.is_duplicate is False
    assert result.final_score == 0.0


def test_identical_vector_is_duplicate(svc, cfg):
    inp = EmbeddingInput(title="Aynı haber", source="a.com")
    text_emb = svc.embed(inp)

    candidates = [{
        "id": "n001",
        "text_vector": text_emb.vector,
        "kaynak_listesi": ["a.com"],
    }]

    result = svc.decide_duplicate(text_emb, candidates, "b.com")
    assert result.is_duplicate is True
    assert result.final_score >= cfg.duplicate_threshold


def test_different_vector_is_not_duplicate(svc):
    t1 = svc.embed(EmbeddingInput(title="Yangın haberi Gebze", source="a.com"))
    t2 = svc.embed(EmbeddingInput(title="Kültür sanat etkinliği İzmit", source="b.com"))

    candidates = [{"id": "n002", "text_vector": t2.vector, "kaynak_listesi": ["b.com"]}]
    result = svc.decide_duplicate(t1, candidates, "a.com")
    assert result.is_duplicate is False


def test_kaynak_listesi_merged_on_duplicate(svc):
    inp = EmbeddingInput(title="Aynı haber", source="a.com")
    text_emb = svc.embed(inp)

    candidates = [{"id": "n001", "text_vector": text_emb.vector, "kaynak_listesi": ["a.com"]}]
    result = svc.decide_duplicate(text_emb, candidates, "b.com")

    assert result.is_duplicate is True
    assert "b.com" in result.merged_kaynak_listesi
    assert "a.com" in result.merged_kaynak_listesi


def test_duplicate_source_not_added_twice(svc):
    inp = EmbeddingInput(title="Aynı haber", source="a.com")
    text_emb = svc.embed(inp)

    candidates = [{"id": "n001", "text_vector": text_emb.vector, "kaynak_listesi": ["a.com"]}]
    result = svc.decide_duplicate(text_emb, candidates, "a.com")
    assert result.merged_kaynak_listesi.count("a.com") == 1


def test_debug_field_populated(svc):
    text_emb = svc.embed(EmbeddingInput(title="Test", source="x.com"))
    result = svc.decide_duplicate(text_emb, [], "x.com")
    assert result.debug is not None
    assert "threshold" in result.debug
    assert "candidate_count" in result.debug


def test_factory_falls_back_to_mock_when_optional_text_provider_missing(monkeypatch, cfg):
    class MissingTextProvider:
        def __init__(self):
            raise ImportError("FlagEmbedding missing")

    monkeypatch.setattr(
        "app.services.embedding.local_factory.BGEM3Provider",
        MissingTextProvider,
    )

    service = build_embedding_service_from_factory(
        EmbeddingConfig(
            text_provider="bge-m3",
            text_dimension=1024,
            duplicate_threshold=0.90,
            text_score_weight=1.00,
            cost_log_path=cfg.cost_log_path,
        )
    )

    text_emb = service.embed(
        EmbeddingInput(
            title="Fallback test",
            source="test.com",
        )
    )

    assert text_emb.provider == "mock-text"


def test_factory_uses_remote_text_provider_when_ml_service_configured(monkeypatch, cfg):
    class RemoteTextProviderStub:
        name = "remote-bge-m3"
        dimension = 1024

        def __init__(self, *, base_url: str, timeout_seconds: float, provider: str, dimension: int):
            self.base_url = base_url
            self.timeout_seconds = timeout_seconds
            self.provider = provider
            self.dimension = dimension

        def embed_text(self, text: str):
            return np.ones(self.dimension, dtype=np.float32) / np.sqrt(self.dimension)

    monkeypatch.setattr("app.settings.settings.ml_service_url", "http://ml:8010")
    monkeypatch.setattr(
        "app.services.embedding.factory.RemoteTextProvider",
        RemoteTextProviderStub,
    )

    service = build_embedding_service_from_factory(
        EmbeddingConfig(
            text_provider="bge-m3",
            text_dimension=1024,
            duplicate_threshold=0.90,
            text_score_weight=1.00,
            cost_log_path=cfg.cost_log_path,
        )
    )

    text_emb = service.embed(
        EmbeddingInput(
            title="Remote embedding test",
            source="test.com",
        )
    )

    assert text_emb.provider == "remote-bge-m3"
