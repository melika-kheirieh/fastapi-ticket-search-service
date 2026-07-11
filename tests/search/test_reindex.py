from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.base import Base
from app.models.ticket import Ticket
from app.search.reindex import reindex_tickets


class FakeIndices:
    def __init__(self):
        self.created_indexes = []
        self.deleted_indexes = []

    def exists(self, index: str) -> bool:
        return True

    def delete(self, index: str) -> None:
        self.deleted_indexes.append(index)

    def create(self, index: str, mappings: dict, settings: dict) -> None:
        self.created_indexes.append(
            {
                "index": index,
                "mappings": mappings,
                "settings": settings,
            }
        )


class FakeElasticsearchClient:
    def __init__(self):
        self.indices = FakeIndices()
        self.index_calls = []

    def index(self, index: str, id: str, document: dict) -> None:
        self.index_calls.append(
            {
                "index": index,
                "id": id,
                "document": document,
            }
        )


def test_reindex_tickets_rebuilds_index_from_database_tickets():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    TestingSessionLocal = sessionmaker(bind=engine)

    Base.metadata.create_all(bind=engine)

    db = TestingSessionLocal()

    try:
        db.add_all(
            [
                Ticket(
                    user_id=1,
                    title="Login issue",
                    description="User cannot login",
                    status="open",
                    priority="high",
                    category="auth",
                    tags=["login"],
                ),
                Ticket(
                    user_id=2,
                    title="Payment delay",
                    description="Payment confirmation is delayed",
                    status="pending",
                    priority="medium",
                    category="billing",
                    tags=["payment"],
                ),
            ]
        )
        db.commit()

        client = FakeElasticsearchClient()

        count = reindex_tickets(
            db=db,
            client=client,
            index_name="tickets_test",
        )

        assert count == 2

        assert client.indices.deleted_indexes == ["tickets_test"]
        assert client.indices.created_indexes[0]["index"] == "tickets_test"

        assert [call["id"] for call in client.index_calls] == ["1", "2"]
        assert client.index_calls[0]["document"]["title"] == "Login issue"
        assert client.index_calls[1]["document"]["title"] == "Payment delay"
    finally:
        db.close()