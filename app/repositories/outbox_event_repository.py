from datetime import datetime, timezone, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

from app.models.outbox_event import OutboxEvent


class OutboxEventRepository:
    def __init__(self, db: Session):
        self.db = db

    def add_event(
        self,
        *,
        aggregate_type: str,
        aggregate_id: int,
        event_type: str,
        payload: dict | None = None,
    ) -> OutboxEvent:
        event = OutboxEvent(
            aggregate_type=aggregate_type,
            aggregate_id=aggregate_id,
            event_type=event_type,
            payload=payload if payload is not None else {},
        )

        self.db.add(event)

        return event

    def get_pending_events(self, *, limit: int = 100) -> list[OutboxEvent]:
        stmt = (
            select(OutboxEvent)
            .where(OutboxEvent.status == "pending")
            .order_by(OutboxEvent.created_at.asc(), OutboxEvent.id.asc())
            .limit(limit)
        )

        result = self.db.execute(stmt)

        return list(result.scalars().all())
    
    def get_processable_events(
        self,
        limit: int = 20,
        max_retry_count: int = 3,
        processing_timeout_seconds: int = 300,
    ) -> list[OutboxEvent]:
        processing_deadline = datetime.now(timezone.utc) - timedelta(
            seconds=processing_timeout_seconds
        )

        return (
            self.db.query(OutboxEvent)
            .filter(
                or_(
                    OutboxEvent.status == "pending",
                    and_(
                        OutboxEvent.status == "failed",
                        OutboxEvent.retry_count < max_retry_count,
                    ),
                    and_(
                        OutboxEvent.status == "processing",
                        OutboxEvent.retry_count < max_retry_count,
                        OutboxEvent.updated_at < processing_deadline,
                    ),
                )
            )
            .order_by(OutboxEvent.created_at, OutboxEvent.id)
            .limit(limit)
            .all()
        )

    def mark_processing(self, event: OutboxEvent) -> OutboxEvent:
        event.status = "processing"
        self.db.flush()

        return event

    def mark_processed(self, event: OutboxEvent) -> OutboxEvent:
        event.status = "processed"
        event.processed_at = datetime.now(timezone.utc)
        event.last_error = None
        self.db.flush()

        return event

    def mark_failed(
        self,
        event: OutboxEvent,
        *,
        error: Exception,
    ) -> OutboxEvent:
        event.status = "failed"
        event.retry_count += 1
        event.last_error = str(error)
        self.db.flush()

        return event