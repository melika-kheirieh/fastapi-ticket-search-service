import importlib

import pytest

OUTBOX_BEAT_TASK_KEY = "process-outbox-batch-every-10-seconds"


def _reload_celery_modules():
    import app.core.config
    import app.celery_app

    importlib.reload(app.core.config)
    importlib.reload(app.celery_app)
    return app.celery_app.celery_app


@pytest.fixture(autouse=True)
def isolate_celery_app_modules():
    yield
    _reload_celery_modules()


def test_outbox_beat_schedule_defaults_to_ten_seconds():
    celery_app = _reload_celery_modules()
    schedule_entry = celery_app.conf.beat_schedule[OUTBOX_BEAT_TASK_KEY]

    assert schedule_entry["task"] == "process_outbox_batch"
    assert schedule_entry["schedule"] == 10.0


def test_outbox_beat_schedule_uses_configured_interval(monkeypatch):
    monkeypatch.setenv("OUTBOX_BEAT_SCHEDULE_SECONDS", "2.5")
    celery_app = _reload_celery_modules()
    schedule_entry = celery_app.conf.beat_schedule[OUTBOX_BEAT_TASK_KEY]

    assert schedule_entry["task"] == "process_outbox_batch"
    assert schedule_entry["schedule"] == 2.5


def test_celery_broker_and_result_backend_use_settings(monkeypatch):
    monkeypatch.setenv("CELERY_BROKER_URL", "redis://example:6379/2")
    monkeypatch.setenv("CELERY_RESULT_BACKEND", "redis://example:6379/3")
    celery_app = _reload_celery_modules()

    assert celery_app.conf.broker_url == "redis://example:6379/2"
    assert celery_app.conf.result_backend == "redis://example:6379/3"
