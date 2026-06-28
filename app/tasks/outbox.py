from app.celery_app import celery_app
from app.core.config import settings
from app.db.session import SessionLocal
from app.outbox.processor import OutboxProcessor


@celery_app.task(name="process_outbox_batch")
def process_outbox_batch() -> dict:
    db = SessionLocal()

    try:
        processor = OutboxProcessor(db)
        result = processor.process_events(
            limit=settings.outbox_batch_size,
            max_retry_count=settings.outbox_max_retry_count,
            processing_timeout_seconds=settings.outbox_processing_timeout_seconds,
        )
        return {
            "processed": result.processed,
            "failed": result.failed,
            "skipped": result.skipped,
        }
    finally:
        db.close()