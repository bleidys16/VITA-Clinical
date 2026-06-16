import os
from celery import Celery

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
os.environ.setdefault('CELERY_BROKER_URL', '')
os.environ.setdefault('CELERY_RESULT_BACKEND', '')

app = Celery('vita_clinical')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()