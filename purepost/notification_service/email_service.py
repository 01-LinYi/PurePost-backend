from celery import shared_task
from django.core.mail import EmailMessage
from django.template.loader import render_to_string

from purepost import settings


@shared_task
def send_email_async(subject, to_email, template_name, context, from_email=None):
    from_email = from_email or settings.EMAIL_HOST_USER
    message = render_to_string(template_name, context)
    email = EmailMessage(subject, message, to=to_email, from_email=from_email)
    email.content_subtype = "html"
    email.send()
