from django.db import models
from django.conf import settings

class Post(models.Model):
    """Post model - Content that users can publish, including text, images, and videos"""
    VISIBILITY_CHOICES = (
        ('public', 'Public'),
        ('private', 'Private'),
    )
    
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="posts")
    content = models.TextField(blank=True, null=True)
    image = models.ImageField(upload_to="posts/images/", blank=True, null=True)
    video = models.FileField(upload_to="posts/videos/", blank=True, null=True)
    visibility = models.CharField(max_length=10, choices=VISIBILITY_CHOICES, default='public')
    like_count = models.PositiveIntegerField(default=0)
    share_count = models.PositiveIntegerField(default=0)
    comment_count = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        """Model metadata"""
        db_table = 'content_moderation_post'
        verbose_name = 'Post'
        verbose_name_plural = 'Posts'
        ordering = ['-created_at']  # Default order by creation time descending

    def __str__(self):
        """String representation"""
        return f"Post by {self.user.username} at {self.created_at.strftime('%Y-%m-%d %H:%M')}"
    
    def save(self, *args, **kwargs):
        """Override save method to handle image/video mutual exclusivity"""
        # Ensure at least content, image, or video is present
        if not (self.content or self.image or self.video):
            raise ValueError("Post must have at least content, image, or video")
            
        super().save(*args, **kwargs)


class Folder(models.Model):
    """Folder model - Users can create folders to organize saved posts"""
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="folders")
    name = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        """Model metadata"""
        db_table = 'content_moderation_folder'
        verbose_name = 'Folder'
        verbose_name_plural = 'Folders'
        ordering = ['name']  # Default order by name
        # Ensure users cannot create folders with duplicate names
        constraints = [
            models.UniqueConstraint(fields=['user', 'name'], name='unique_folder_name_per_user')
        ]

    def __str__(self):
        """String representation"""
        return f"{self.name} (by {self.user.username})"


class SavedPost(models.Model):
    """SavedPost model - Users can save posts to folders"""
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="saved_posts")
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name="saved_by")
    folder = models.ForeignKey(Folder, on_delete=models.CASCADE, related_name="saved_posts", null=True, blank=True)
    saved_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        """Model metadata"""
        db_table = 'content_moderation_saved_post'
        verbose_name = 'Saved Post'
        verbose_name_plural = 'Saved Posts'
        ordering = ['-saved_at']  # Default order by save time descending
        # Ensure users cannot save the same post to the same folder multiple times
        constraints = [
            models.UniqueConstraint(fields=['user', 'post', 'folder'], name='unique_saved_post')
        ]

    def __str__(self):
        """String representation"""
        folder_name = self.folder.name if self.folder else "No Folder"
        return f"{self.user.username} saved post #{self.post.id} in {folder_name}"

class Like(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="likes")
    post = models.ForeignKey(
        Post, on_delete=models.CASCADE, related_name="likes")
    liked_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'content_moderation_like'
        verbose_name = 'Like'
        verbose_name_plural = 'Likes'
        ordering = ['-liked_at']
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'post'], name='unique_like')
        ]

    def __str__(self):
        return f"{self.user.username} liked post #{self.post.id}"
