from datetime import datetime, timezone

from app.search.queries import (
    build_ticket_search_body,
    build_ticket_search_query,
    search_tickets,
)


class FakeElasticsearchClient:
    def __init__(self):
        self.search_calls = []

    def search(self, index: str, body: dict) -> dict:
        self.search_calls.append(
            {
                "index": index,
                "body": body,
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
            "body": {
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
                "from": 5,
                "size": 10,
                "sort": [
                    {"created_at": {"order": "desc"}},
                    {"id": {"order": "desc"}},
                ],
            },
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
        user_id=7,
        limit=20,
        offset=0,
        index_name="tickets_test",
    )

    assert client.search_calls[0]["body"]["query"] == {
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
                {"term": {"status": "open"}},
                {"term": {"priority": "high"}},
                {"term": {"category": "payment"}},
                {"term": {"tags": "checkout"}},
                {"term": {"user_id": 7}},
            ],
        }
    }


def test_build_ticket_search_query_returns_bool_query_with_filters():
    query = build_ticket_search_query(
        query="payment",
        status="open",
        priority="high",
        category="payment",
        tag="checkout",
    )

    assert query == {
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
                {"term": {"status": "open"}},
                {"term": {"priority": "high"}},
                {"term": {"category": "payment"}},
                {"term": {"tags": "checkout"}},
            ],
        }
    }


def test_build_ticket_search_query_uses_match_all_without_text_query():
    query = build_ticket_search_query(status="open")

    assert query == {
        "bool": {
            "must": [
                {
                    "match_all": {}
                }
            ],
            "filter": [
                {"term": {"status": "open"}},
            ],
        }
    }


def test_build_ticket_search_query_adds_created_at_range_filter():
    created_from = datetime(2026, 6, 1, tzinfo=timezone.utc)
    created_to = datetime(2026, 6, 24, tzinfo=timezone.utc)

    query = build_ticket_search_query(
        created_from=created_from,
        created_to=created_to,
    )

    assert query == {
        "bool": {
            "must": [
                {
                    "match_all": {}
                }
            ],
            "filter": [
                {
                    "range": {
                        "created_at": {
                            "gte": "2026-06-01T00:00:00+00:00",
                            "lte": "2026-06-24T00:00:00+00:00",
                        }
                    }
                }
            ],
        }
    }


def test_build_ticket_search_body_adds_pagination_and_stable_sort():
    body = build_ticket_search_body(
        query="payment",
        status="open",
        limit=10,
        offset=20,
    )

    assert body == {
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
                "filter": [
                    {"term": {"status": "open"}},
                ],
            }
        },
        "from": 20,
        "size": 10,
        "sort": [
            {"created_at": {"order": "desc"}},
            {"id": {"order": "desc"}},
        ],
    }