from types import SimpleNamespace

from app.tasks import outbox


class FakeSession:
    def __init__(self):
        self.closed = False

    def close(self):
        self.closed = True


class FakeOutboxProcessor:
    instances = []

    def __init__(self, db):
        self.db = db
        self.process_events_called = False
        FakeOutboxProcessor.instances.append(self)

    def process_events(self):
        self.process_events_called = True
        return SimpleNamespace(
            processed=2,
            failed=1,
            skipped=0,
        )


def test_process_outbox_batch_runs_processor_and_closes_session(monkeypatch):
    FakeOutboxProcessor.instances = []
    session = FakeSession()

    monkeypatch.setattr(outbox, "SessionLocal", lambda: session)
    monkeypatch.setattr(outbox, "OutboxProcessor", FakeOutboxProcessor)

    result = outbox.process_outbox_batch()

    assert result == {
        "processed": 2,
        "failed": 1,
        "skipped": 0,
    }
    assert len(FakeOutboxProcessor.instances) == 1
    assert FakeOutboxProcessor.instances[0].db is session
    assert FakeOutboxProcessor.instances[0].process_events_called is True
    assert session.closed is True