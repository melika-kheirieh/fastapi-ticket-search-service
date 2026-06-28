from app.core.config import Settings


def test_outbox_runtime_config_defaults():
    settings = Settings()

    assert settings.outbox_batch_size == 20
    assert settings.outbox_max_retry_count == 3
    assert settings.outbox_processing_timeout_seconds == 300
    assert settings.outbox_beat_schedule_seconds == 10.0