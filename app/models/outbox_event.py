from sqlalchemy import (
    CheckConstraint,
    Column,
    DateTime,
    Index,
    Integer,
    JSON,
    String,
    Text,
    func,
    text,
)

from app.db.base import Base


class OutboxEvent(Base):
    __tablename__ = "outbox_events"

    id = Column(Integer, primary_key=True)

    aggregate_type = Column(String(64), nullable=False)
    aggregate_id = Column(Integer, nullable=False)
    event_type = Column(String(128), nullable=False)

    status = Column(
        String(32),
        nullable=False,
        default="pending",
        server_default=text("'pending'"),
    )
    payload = Column(
        JSON,
        nullable=False,
        default=dict,
        server_default=text("'{}'"),
    )
    retry_count = Column(
        Integer,
        nullable=False,
        default=0,
        server_default=text("0"),
    )

    last_error = Column(Text, nullable=True)
    processed_at = Column(DateTime(timezone=True), nullable=True)
    next_attempt_at = Column(DateTime(timezone=True), nullable=True, index=True)

    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    __table_args__ = (
        CheckConstraint(
            "status IN ('pending', 'processing', 'processed', 'failed')",
            name="ck_outbox_events_status",
        ),
        Index("ix_outbox_events_status_created_at", "status", "created_at"),
        Index("ix_outbox_events_aggregate", "aggregate_type", "aggregate_id"),
    )
