from app.search.client import (
    create_ticket_index_if_missing,
    recreate_ticket_index,
)


class FakeIndices:
    def __init__(self, exists_result: bool):
        self.exists_result = exists_result
        self.created_indexes = []
        self.deleted_indexes = []

    def exists(self, index: str) -> bool:
        return self.exists_result

    def create(self, index: str, mappings: dict, settings: dict) -> None:
        self.created_indexes.append(
            {
                "index": index,
                "mappings": mappings,
                "settings": settings,
            }
        )

    def delete(self, index: str) -> None:
        self.deleted_indexes.append(index)


class FakeElasticsearchClient:
    def __init__(self, exists_result: bool):
        self.indices = FakeIndices(exists_result)


def test_create_ticket_index_if_missing_creates_index_when_absent():
    client = FakeElasticsearchClient(exists_result=False)

    created = create_ticket_index_if_missing(client, index_name="tickets_test")

    assert created is True
    assert client.indices.created_indexes[0]["index"] == "tickets_test"
    assert "properties" in client.indices.created_indexes[0]["mappings"]
    assert client.indices.deleted_indexes == []


def test_create_ticket_index_if_missing_skips_existing_index():
    client = FakeElasticsearchClient(exists_result=True)

    created = create_ticket_index_if_missing(client, index_name="tickets_test")

    assert created is False
    assert client.indices.created_indexes == []
    assert client.indices.deleted_indexes == []


def test_recreate_ticket_index_deletes_existing_index_then_creates_it():
    client = FakeElasticsearchClient(exists_result=True)

    recreate_ticket_index(client, index_name="tickets_test")

    assert client.indices.deleted_indexes == ["tickets_test"]
    assert client.indices.created_indexes[0]["index"] == "tickets_test"
    assert "properties" in client.indices.created_indexes[0]["mappings"]