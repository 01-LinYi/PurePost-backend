from django.core.mail import EmailMessage
from django.template.loader import render_to_string
from django.conf import settings


def send_email(subject, to_email, template_name, context, from_email=None):
    """
    General email service to send emails.
    Args:
        subject (str): Email subject
        to_email (list): List of recipients
        template_name (str): Path to the email template
        context (dict): Context for template rendering
        from_email (str): Sender email (optional)
    """
    from_email = from_email or settings.DEFAULT_FROM_EMAIL  # Use default if not specified
    message = render_to_string(template_name, context)  # Render the email template with context
    email = EmailMessage(subject=subject, body=message, to=to_email, from_email=from_email)
    email.content_subtype = "html"  # Specify email type as HTML
    email.send()  # Send the email
