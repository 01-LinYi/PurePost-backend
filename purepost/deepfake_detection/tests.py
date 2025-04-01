from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model
from unittest.mock import patch
from rest_framework.test import APIClient
from rest_framework import status

from purepost.content_moderation.models import Post
from .models import ImageAnalysis

User = get_user_model()


class ImageAnalysisTests(TestCase):
    """Tests for the image analysis deepfake detection functionality"""

    def setUp(self):
        # Create test user
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpassword'
        )

        # Create a post for testing
        self.post = Post.objects.create(
            user=self.user,
            content="Test content",
            image="https://example.com/image.jpg",
            deepfake_status='not_analyzed'
        )

        # Set up API client
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

        # Create admin user
        self.admin = User.objects.create_user(
            username='admin',
            email='admin@example.com',
            password='adminpassword',
            is_staff=True
        )

    def test_get_nonexistent_analysis(self):
        """Test retrieving analysis for a post that hasn't been analyzed"""
        url = reverse('post-analysis', args=[self.post.id])
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    @patch('purepost.deepfake_detection.tasks.process_image_analysis.delay')
    def test_create_analysis(self, mock_task):
        """Test creating a new analysis for a post"""
        mock_task.return_value.id = 'fake-task-id'

        url = reverse('post-analysis', args=[self.post.id])
        response = self.client.post(url)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(ImageAnalysis.objects.count(), 1)

        # Verify post status updated
        self.post.refresh_from_db()
        self.assertEqual(self.post.deepfake_status, 'analyzing')

        # Verify task was called
        mock_task.assert_called_once()

    def test_unauthorized_access(self):
        """Test that users cannot access other users' post analyses"""
        # Create another user
        other_user = User.objects.create_user(
            username='otheruser',
            email='other@example.com',
            password='otherpassword'
        )

        # Create a post for the other user
        other_post = Post.objects.create(
            user=other_user,
            content="Other content",
            image="https://example.com/other.jpg"
        )

        # Try to access the other user's post analysis
        url = reverse('post-analysis', args=[other_post.id])
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_completed_analysis(self):
        """Test retrieving a completed analysis"""
        # Create a completed analysis
        analysis = ImageAnalysis.objects.create(
            post=self.post,
            status='completed',
            is_deepfake=True,
            deepfake_score=0.85
        )

        # Update post status
        self.post.deepfake_status = 'flagged'
        self.post.deepfake_score = 0.85
        self.post.save()

        url = reverse('post-analysis', args=[self.post.id])
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['is_deepfake'], True)
        self.assertEqual(response.data['deepfake_score'], 0.85)

    @patch('purepost.deepfake_detection.tasks.process_image_analysis.delay')
    def test_retry_failed_analysis(self, mock_task):
        """Test retrying a failed analysis"""
        mock_task.return_value.id = 'retry-task-id'

        # Create a failed analysis
        analysis = ImageAnalysis.objects.create(
            post=self.post,
            status='failed',
            failure_reason='Test failure'
        )

        # Update post status
        self.post.deepfake_status = 'analysis_failed'
        self.post.save()

        url = reverse('post-analysis-retry', args=[self.post.id])
        response = self.client.post(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Verify analysis status updated
        analysis.refresh_from_db()
        self.assertEqual(analysis.status, 'pending')
        self.assertIsNone(analysis.failure_reason)

        # Verify post status updated
        self.post.refresh_from_db()
        self.assertEqual(self.post.deepfake_status, 'analyzing')

    def test_admin_access(self):
        """Test that admins can access any user's post analysis"""
        # Set up admin client
        admin_client = APIClient()
        admin_client.force_authenticate(user=self.admin)

        # Create an analysis
        analysis = ImageAnalysis.objects.create(
            post=self.post,
            status='completed',
            is_deepfake=False,
            deepfake_score=0.15
        )

        url = reverse('post-analysis', args=[self.post.id])
        response = admin_client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    @patch('purepost.deepfake_detection.tasks.process_image_analysis.delay')
    def test_prevent_duplicate_analysis(self, mock_task):
        """Test that we can't create duplicate analyses for a post"""
        mock_task.return_value.id = 'task-id'

        # Create an in-progress analysis
        ImageAnalysis.objects.create(
            post=self.post,
            status='processing'
        )

        # Update post status
        self.post.deepfake_status = 'analyzing'
        self.post.save()

        # Try to create another analysis
        url = reverse('post-analysis', args=[self.post.id])
        response = self.client.post(url)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        # Verify only one analysis exists
        self.assertEqual(ImageAnalysis.objects.count(), 1)
