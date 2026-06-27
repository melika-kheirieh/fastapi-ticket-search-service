from datetime import datetime, timedelta, timezone

from sqlalchemy import and_, or_, select
from sqlalchemy.orm import Session

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
        stmt = self._build_processable_events_stmt(
            limit=limit,
            max_retry_count=max_retry_count,
            processing_timeout_seconds=processing_timeout_seconds,
            lock_rows=False,
        )

        result = self.db.execute(stmt)
        return list(result.scalars().all())

    def claim_processable_events(
        self,
        limit: int = 20,
        max_retry_count: int = 3,
        processing_timeout_seconds: int = 300,
    ) -> list[OutboxEvent]:
        stmt = self._build_processable_events_stmt(
            limit=limit,
            max_retry_count=max_retry_count,
            processing_timeout_seconds=processing_timeout_seconds,
            lock_rows=True,
        )

        result = self.db.execute(stmt)
        events = list(result.scalars().all())

        for event in events:
            event.status = "processing"
            event.processed_at = None
            event.next_attempt_at = None

        self.db.flush()
        return events

    def _build_processable_events_stmt(
        self,
        *,
        limit: int,
        max_retry_count: int,
        processing_timeout_seconds: int,
        lock_rows: bool,
    ):
        now = datetime.now(timezone.utc)
        processing_deadline = now - timedelta(seconds=processing_timeout_seconds)

        stmt = (
            select(OutboxEvent)
            .where(
                and_(
                    or_(
                        OutboxEvent.next_attempt_at.is_(None),
                        OutboxEvent.next_attempt_at <= now,
                    ),
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
                    ),
                )
            )
            .order_by(OutboxEvent.created_at.asc(), OutboxEvent.id.asc())
            .limit(limit)
        )

        if lock_rows:
            stmt = stmt.with_for_update(skip_locked=True)

        return stmt

    def mark_processing(self, event: OutboxEvent) -> OutboxEvent:
        event.status = "processing"
        self.db.flush()
        return event

    def mark_processed(self, event: OutboxEvent) -> OutboxEvent:
        event.status = "processed"
        event.processed_at = datetime.now(timezone.utc)
        event.last_error = None
        event.next_attempt_at = None
        self.db.flush()
        return event

    def mark_failed(
        self,
        event: OutboxEvent,
        *,
        error: Exception,
        retry_delay_seconds: int | None = None,
    ) -> OutboxEvent:
        event.status = "failed"
        event.retry_count += 1
        event.last_error = str(error)
        event.next_attempt_at = None

        if retry_delay_seconds is not None:
            event.next_attempt_at = datetime.now(timezone.utc) + timedelta(
                seconds=retry_delay_seconds
            )

        self.db.flush()
        return event
