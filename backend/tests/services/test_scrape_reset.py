from app.services.scrape_reset import (
    SCRAPED_DATA_COLLECTIONS,
    ScrapeRefreshCleanupResult,
    ScrapeResetResult,
    cleanup_pending_refresh_data,
    cleanup_stale_refresh_data,
    reset_scraped_news_data,
)


class FakeDeleteResult:
    def __init__(self, deleted_count: int):
        self.deleted_count = deleted_count


class FakeCollection:
    def __init__(self, deleted_count: int):
        self.deleted_count = deleted_count
        self.calls: list[dict] = []

    def delete_many(self, query: dict):
        self.calls.append(query)
        return FakeDeleteResult(self.deleted_count)


class FakeRawDocumentCollection(FakeCollection):
    def __init__(self, deleted_count: int, documents: list[dict]):
        super().__init__(deleted_count)
        self.documents = documents
        self.find_calls: list[tuple[dict, dict]] = []

    def find(self, query: dict, projection: dict):
        self.find_calls.append((query, projection))
        return list(self.documents)


class FakeDatabase:
    def __init__(self):
        self.collections = {
            "raw_documents": FakeRawDocumentCollection(12, []),
            "source_records": FakeCollection(8),
            "crawl_sessions": FakeCollection(3),
            "sources": FakeCollection(99),
        }

    def __getitem__(self, name: str):
        return self.collections[name]


def test_reset_scraped_news_data_only_clears_target_collections():
    database = FakeDatabase()

    result = reset_scraped_news_data(database)

    assert isinstance(result, ScrapeResetResult)
    assert result.deleted_counts == {
        "raw_documents": 12,
        "source_records": 8,
        "crawl_sessions": 3,
    }
    assert result.total_deleted == 23

    for collection_name in SCRAPED_DATA_COLLECTIONS:
        assert database.collections[collection_name].calls == [{}]

    assert database.collections["sources"].calls == []


def test_cleanup_stale_refresh_data_removes_only_documents_outside_active_generation():
    stale_raw_document_id = "stale-raw-doc"
    database = FakeDatabase()
    database.collections["raw_documents"] = FakeRawDocumentCollection(
        1,
        [{"_id": stale_raw_document_id}],
    )
    database.collections["source_records"] = FakeCollection(1)

    result = cleanup_stale_refresh_data(
        database,
        active_generation="generation-live",
    )

    assert isinstance(result, ScrapeRefreshCleanupResult)
    assert result.deleted_counts == {
        "source_records": 1,
        "raw_documents": 1,
    }
    assert result.generation == "generation-live"
    assert result.mode == "activate"
    assert result.total_deleted == 2
    assert database.collections["raw_documents"].find_calls == [
        (
            {"dataset_generation": {"$ne": "generation-live"}},
            {"_id": 1},
        )
    ]
    assert database.collections["source_records"].calls == [
        {"raw_document_id": {"$in": [stale_raw_document_id]}}
    ]
    assert database.collections["raw_documents"].calls == [{"_id": {"$in": [stale_raw_document_id]}}]


def test_cleanup_pending_refresh_data_discards_candidate_generation():
    database = FakeDatabase()
    database.collections["raw_documents"] = FakeRawDocumentCollection(
        2,
        [{"_id": "candidate-1"}, {"_id": "candidate-2"}],
    )
    database.collections["source_records"] = FakeCollection(2)

    result = cleanup_pending_refresh_data(
        database,
        pending_generation="generation-candidate",
    )

    assert result.deleted_counts == {
        "source_records": 2,
        "raw_documents": 2,
    }
    assert result.generation == "generation-candidate"
    assert result.mode == "discard"
    assert database.collections["raw_documents"].find_calls == [
        (
            {"dataset_generation": "generation-candidate"},
            {"_id": 1},
        )
    ]
