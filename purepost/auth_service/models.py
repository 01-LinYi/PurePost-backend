from django.contrib.auth.models import AbstractUser
from django.db import models

class User(AbstractUser):
    email = models.EmailField(unique=True)
    is_active = models.BooleanField(default=True)
    is_verified = models.BooleanField(default=False)

    # followings = models.ManyToManyField('self', symmetrical=False, related_name="followers", blank=True)

    is_private = models.BooleanField(default=False)

    def __str__(self):
        return self.username
    
    @property
    def is_admin(self):
        return self.is_staff
    
    def promote_to_admin(self):
        """upgrade to admin"""
        if not self.is_staff:
            self.is_staff = True
            self.save(update_fields=['is_staff'])
        return self
    
    def demote_from_admin(self):
        """downgrade from admin"""
        # we don't want to demote superuser
        if not self.is_superuser and self.is_staff:
            self.is_staff = False
            self.save(update_fields=['is_staff'])
        return self
    
    '''
    def follow(self, user):
        if user != self:
            self.followings.add(user)

    def unfollow(self, user):
        self.followings.remove(user)
    '''