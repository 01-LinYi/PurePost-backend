from django.contrib.auth.models import AbstractUser
from django.db import models

class User(AbstractUser):
    email = models.EmailField(unique=True)
    is_active = models.BooleanField(default=True)

    followings = models.ManyToManyField('self', symmetrical=False, related_name="followers", blank=True)

    def __str__(self):
        return self.username
    
    def follow(self, user):
        if user != self:
            self.followings.add(user)

    def unfollow(self, user):
        self.followings.remove(user)