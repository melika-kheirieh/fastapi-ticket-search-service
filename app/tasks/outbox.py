from app.celery_app import celery_app
from app.db.session import SessionLocal
from app.outbox.processor import OutboxProcessor


@celery_app.task(name="process_outbox_batch")
def process_outbox_batch() -> dict:
    db = SessionLocal()

    try:
        processor = OutboxProcessor(db)
        return processor.process_events()
    finally:
        db.close()