import os
if os.environ.get('CELERY_BROKER_URL'):
    from .celery import app as celery_app
    __all__ = ('celery_app',)