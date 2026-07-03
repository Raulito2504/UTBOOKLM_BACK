from src.core.config import get_settings


try:
    from celery import Celery
except ImportError:
    Celery = None


settings = get_settings()

if Celery is None:
    celery_app = None
else:
    celery_app = Celery(
        "backend",
        broker=settings.broker_url,
        backend=settings.result_backend_url,
    )
    celery_app.conf.update(task_always_eager=False)
