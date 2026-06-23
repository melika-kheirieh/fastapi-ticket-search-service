from app.search.indexer import delete_ticket_document, index_ticket_document


class FakeElasticsearchClient:
    def __init__(self):
        self.index_calls = []
        self.delete_calls = []
        self.options_calls = []

    def index(self, index: str, id: str, document: dict) -> None:
        self.index_calls.append(
            {
                "index": index,
                "id": id,
                "document": document,
            }
        )

    def options(self, ignore_status: list[int]):
        self.options_calls.append({"ignore_status": ignore_status})
        return self

    def delete(self, index: str, id: str) -> None:
        self.delete_calls.append(
            {
                "index": index,
                "id": id,
            }
        )


def test_index_ticket_document_uses_ticket_id_as_elasticsearch_id():
    client = FakeElasticsearchClient()
    document = {
        "id": 42,
        "title": "Payment failed",
    }

    index_ticket_document(
        client=client,
        document=document,
        index_name="tickets_test",
    )

    assert client.index_calls == [
        {
            "index": "tickets_test",
            "id": "42",
            "document": document,
        }
    ]


def test_delete_ticket_document_ignores_missing_document():
    client = FakeElasticsearchClient()

    delete_ticket_document(
        client=client,
        ticket_id=42,
        index_name="tickets_test",
    )

    assert client.options_calls == [{"ignore_status": [404]}]
    assert client.delete_calls == [
        {
            "index": "tickets_test",
            "id": "42",
        }
    ]