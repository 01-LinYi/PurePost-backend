import os
from celery import Celery
from celery.schedules import crontab 
from django.conf import settings

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'purepost.settings')

app = Celery('purepost')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()

app.conf.beat_schedule = {
    'publish-scheduled-posts-every-minute': {
        'task': 'content_moderation.tasks.publish_scheduled_posts',
        'schedule': crontab(minute='*/1'),
        'options': {
            'expires': 30,
            'time_limit': 300,
        },
    },
}

app.conf.timezone = 'UTC'
app.conf.task_serializer = 'json'
app.conf.result_serializer = 'json'
app.conf.accept_content = ['json']

@app.task(bind=True, ignore_result=True)
def debug_task(self):
    print(f'Request: {self.request!r}')