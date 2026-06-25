from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.db.unit_of_work import UnitOfWork
from app.models.outbox_event import OutboxEvent
from app.search.client import create_elasticsearch_client
from app.search.documents import ticket_to_search_document
from app.search.indexer import delete_ticket_document, index_ticket_document


@dataclass
class OutboxProcessingResult:
    processed: int = 0
    failed: int = 0
    skipped: int = 0


class OutboxProcessor:
    def __init__(self, db: Session, search_client=None):
        self.uow = UnitOfWork(db)
        self.search_client = search_client or create_elasticsearch_client()

    def process_events(
        self,
        limit: int = 20,
        max_retry_count: int = 3,
        processing_timeout_seconds: int = 300,
    ) -> OutboxProcessingResult:
        events = self.uow.outbox_events.get_processable_events(
            limit=limit,
            max_retry_count=max_retry_count,
            processing_timeout_seconds=processing_timeout_seconds,
        )
        result = OutboxProcessingResult()

        for event in events:
            was_processed = self._process_one_event(event)

            if was_processed:
                result.processed += 1
            else:
                result.failed += 1

        return result

    def _process_one_event(self, event: OutboxEvent) -> bool:
        self.uow.outbox_events.mark_processing(event)
        self.uow.commit()

        try:
            self._sync_event(event)
        except Exception as exc:
            self.uow.outbox_events.mark_failed(event, error=exc)
            self.uow.commit()
            return False

        self.uow.outbox_events.mark_processed(event)
        self.uow.commit()
        return True

    def _sync_event(self, event: OutboxEvent) -> None:
        if event.event_type in {"ticket.created", "ticket.updated"}:
            self._index_ticket(event.aggregate_id)
            return

        if event.event_type == "ticket.deleted":
            self._delete_ticket_document(event.aggregate_id)
            return

        raise ValueError(f"Unsupported outbox event type: {event.event_type}")

    def _index_ticket(self, ticket_id: int) -> None:
        ticket = self.uow.tickets.get_by_id(ticket_id)

        if ticket is None:
            return

        document = ticket_to_search_document(ticket)
        index_ticket_document(self.search_client, document)

    def _delete_ticket_document(self, ticket_id: int) -> None:
        delete_ticket_document(self.search_client, ticket_id)