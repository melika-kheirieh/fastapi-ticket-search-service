from app.celery_app import celery_app
from app.db.session import SessionLocal
from app.outbox.processor import OutboxProcessor


@celery_app.task(name="process_outbox_batch")
def process_outbox_batch() -> dict:
    db = SessionLocal()

    try:
        processor = OutboxProcessor(db)
        result = processor.process_events()
        return {
            "processed": result.processed,
            "failed": result.failed,
            "skipped": result.skipped,
        }
    finally:
        db.close()