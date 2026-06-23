from app.search.queries import search_tickets


class FakeElasticsearchClient:
    def __init__(self):
        self.search_calls = []

    def search(
        self,
        index: str,
        query: dict,
        from_: int,
        size: int,
    ) -> dict:
        self.search_calls.append(
            {
                "index": index,
                "query": query,
                "from_": from_,
                "size": size,
            }
        )

        return {
            "hits": {
                "hits": [
                    {
                        "_source": {
                            "id": 1,
                            "title": "Payment failed",
                            "description": "User payment failed during checkout",
                            "status": "open",
                        }
                    }
                ]
            }
        }


def test_search_tickets_searches_title_and_description():
    client = FakeElasticsearchClient()

    results = search_tickets(
        client=client,
        query="payment",
        limit=10,
        offset=5,
        index_name="tickets_test",
    )

    assert client.search_calls == [
        {
            "index": "tickets_test",
            "query": {
                "bool": {
                    "must": [
                        {
                            "multi_match": {
                                "query": "payment",
                                "fields": ["title", "description"],
                            }
                        }
                    ],
                    "filter": [],
                }
            },
            "from_": 5,
            "size": 10,
        }
    ]

    assert results == [
        {
            "id": 1,
            "title": "Payment failed",
            "description": "User payment failed during checkout",
            "status": "open",
        }
    ]


def test_search_tickets_adds_exact_filters_when_provided():
    client = FakeElasticsearchClient()

    search_tickets(
        client=client,
        query="payment",
        status="open",
        priority="high",
        category="payment",
        tag="checkout",
        limit=20,
        offset=0,
        index_name="tickets_test",
    )

    assert client.search_calls[0]["query"] == {
        "bool": {
            "must": [
                {
                    "multi_match": {
                        "query": "payment",
                        "fields": ["title", "description"],
                    }
                }
            ],
            "filter": [
                {
                    "term": {
                        "status": "open",
                    }
                },
                {
                    "term": {
                        "priority": "high",
                    }
                },
                {
                    "term": {
                        "category": "payment",
                    }
                },
                {
                    "term": {
                        "tags": "checkout",
                    }
                },
            ],
        }
    }
