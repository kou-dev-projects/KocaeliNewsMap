from app.services.scrape_reset import (
    SCRAPED_DATA_COLLECTIONS,
    ScrapeResetResult,
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


class FakeDatabase:
    def __init__(self):
        self.collections = {
            "raw_documents": FakeCollection(12),
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
