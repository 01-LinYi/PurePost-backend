from django.db import models
from django.conf import settings


class Post(models.Model):
    """Post model - Content that users can publish, including text, images, and videos"""
    VISIBILITY_CHOICES = (
        ('public', 'Public'),
        ('private', 'Private'),
        ('friends', 'Friends-Only'),
    )
    DEEPFAKE_CHOICES = (
        ('not_analyzed', 'Not Analyzed'),
        ('analyzing', 'Analyzing'),
        ('flagged', 'Flagged as Deepfake'),
        ('not_flagged', 'Not Flagged (Real)'),
        ('analysis_failed', 'Analysis Failed')
    )

    STATUS_CHOICES = (
        ('draft', 'Draft'),
        ('published', 'Published'),
    )

    user = models.ForeignKey(settings.AUTH_USER_MODEL,
                             on_delete=models.CASCADE, related_name="posts")
    content = models.TextField(blank=True, null=True)
    image = models.ImageField(upload_to="posts/images/", blank=True, null=True)
    video = models.FileField(upload_to="posts/videos/", blank=True, null=True)
    visibility = models.CharField(
        max_length=10, choices=VISIBILITY_CHOICES, default='public')
    like_count = models.PositiveIntegerField(default=0)
    share_count = models.PositiveIntegerField(default=0)
    comment_count = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    pinned = models.BooleanField(default=False)
    disclaimer = models.CharField(max_length=200, blank=True, null=True)
    deepfake_status = models.CharField(
        max_length=20,
        choices=DEEPFAKE_CHOICES,
        default='not_analyzed',
        help_text="Status of deepfake detection"
    )
    deepfake_score = models.FloatField(
        null=True,
        blank=True,
        help_text="Confidence score for deepfake detection"
    )
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='published')
    caption = models.CharField(max_length=100, blank=True, null=True)
    # Add tags field - using JSONField to store array of strings
    tags = models.JSONField(default=list, blank=True, null=True)

    # likes = models.ManyToManyField(settings.AUTH_USER_MODEL, through="Like", related_name="liked_posts")
    # shares = models.ManyToManyField(settings.AUTH_USER_MODEL, through="Share", related_name="shared_posts")
    # comments = models.ManyToManyField(settings.AUTH_USER_MODEL, through="Comment", related_name="commented_posts")

    class Meta:
        """Model metadata"""
        db_table = 'content_moderation_post'
        verbose_name = 'Post'
        verbose_name_plural = 'Posts'
        ordering = ['-created_at']  # Default order by creation time descending

    def __str__(self):
        """String representation"""
        status_text = f" ({self.get_status_display()})" if self.status != 'published' else ""
        return f"Post by {self.user.username} at {self.created_at.strftime('%Y-%m-%d %H:%M')}"

    def save(self, *args, **kwargs):
        """Override save method to handle image/video mutual exclusivity"""
        # Ensure at least content, image, or video is present for non-draft
        if self.status != 'draft':
            if not (self.content or self.image or self.video):
                raise ValueError("Post must have at least content, image, or video")

        if self.tags is None:
            self.tags = []

        if self.tags is None:
            self.tags = []

        super().save(*args, **kwargs)


class Folder(models.Model):
    """Folder model - Users can create folders to organize saved posts"""
    user = models.ForeignKey(settings.AUTH_USER_MODEL,
                             on_delete=models.CASCADE, related_name="folders")
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
            models.UniqueConstraint(
                fields=['user', 'name'], name='unique_folder_name_per_user')
        ]

    def __str__(self):
        """String representation"""
        return f"{self.name} (by {self.user.username})"


class SavedPost(models.Model):
    """SavedPost model - Users can save posts to folders"""
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="saved_posts")
    post = models.ForeignKey(
        Post, on_delete=models.CASCADE, related_name="saved_by")
    folder = models.ForeignKey(
        Folder, on_delete=models.CASCADE, related_name="saved_posts", null=True, blank=True)
    saved_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        """Model metadata"""
        db_table = 'content_moderation_saved_post'
        verbose_name = 'Saved Post'
        verbose_name_plural = 'Saved Posts'
        ordering = ['-saved_at']  # Default order by save time descending
        # Ensure users cannot save the same post to the same folder multiple times
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'post', 'folder'], name='unique_saved_post')
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


class Share(models.Model):
    """Share model - Users can share posts"""
    user = models.ForeignKey(settings.AUTH_USER_MODEL,
                             on_delete=models.CASCADE, related_name="shares")
    post = models.ForeignKey(
        Post, on_delete=models.CASCADE, related_name="shares")
    shared_at = models.DateTimeField(auto_now_add=True)
    comment = models.TextField(blank=True, null=True)

    class Meta:
        db_table = 'content_moderation_share'
        verbose_name = 'Share'
        verbose_name_plural = 'Shares'
        ordering = ['-shared_at']
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'post'], name='unique_share')
        ]

    def __str__(self):
        return f"{self.user.username} shared post #{self.post.id}"


class Comment(models.Model):
    """Comment model - Users can reply to posts"""
    user = models.ForeignKey(settings.AUTH_USER_MODEL,
                             on_delete=models.CASCADE, related_name="comments")
    post = models.ForeignKey(
        Post, on_delete=models.CASCADE, related_name="comments")
    content = models.TextField()
    parent = models.ForeignKey(
        'self', on_delete=models.CASCADE, related_name="replies", null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'content_moderation_comment'
        verbose_name = 'Comment'
        verbose_name_plural = 'Comments'
        ordering = ['created_at']

    def __str__(self):
        return f"{self.user.username} commented on post #{self.post.id}"

    def delete(self, *args, **kwargs):
        """Override delete method to handle comment count and replies"""
        # If this comment has replies, delete them first
        if self.replies.exists():
            self.replies.all().delete()

        # Decrement the comment count on the associated post
        self.post.comment_count = models.F('comment_count') - 1
        self.post.save()

        # Call the superclass delete method to actually delete the comment
        super().delete(*args, **kwargs)


class Report(models.Model):
    """Report model - Users can report posts"""
    REPORT_REASONS = (
        ('inappropriate', 'Inappropriate Content'),
        ('deepfake', 'Deepfake Content'),
        ('spam', 'Spam'),
        ('harassment', 'Harassment'),
        ('misinformation', 'Misinformation'),
        ('copyright', 'Copyright Violation'),
        ('other', 'Other'),
    )

    REPORT_STATUS = (
        ('pending', 'Pending'),
        ('reviewing', 'Under Review'),
        ('resolved', 'Resolved'),
        ('rejected', 'Rejected by Admin'),
    )

    post = models.ForeignKey(
        Post, on_delete=models.CASCADE, related_name='reports')
    reporter = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='submitted_reports')
    reason = models.CharField(max_length=20, choices=REPORT_REASONS)
    additional_info = models.TextField(blank=True, null=True)
    status = models.CharField(
        max_length=10, choices=REPORT_STATUS, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('post', 'reporter')
