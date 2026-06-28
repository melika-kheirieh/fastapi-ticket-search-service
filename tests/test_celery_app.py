from app.celery_app import celery_app
from app.core.config import settings


def test_outbox_beat_schedule_uses_configured_interval():
    schedule_entry = celery_app.conf.beat_schedule[
        "process-outbox-batch-every-10-seconds"
    ]

    assert schedule_entry["task"] == "process_outbox_batch"
    assert schedule_entry["schedule"] == settings.outbox_beat_schedule_seconds