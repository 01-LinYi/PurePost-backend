from django.db import models
from django.conf import settings
from django.db.models import Q


class Feedback(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL,
                             on_delete=models.CASCADE)
    feedback_type = models.CharField(
        max_length=50)  # name of the feedback sheet
    # to check if this type of feedback is finished
    is_finished = models.BooleanField(default=False)
    content = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [
            ('user', 'feedback_type'),
        ]

    def __str__(self):
        return f"{self.user} - {self.feedback_type}"
