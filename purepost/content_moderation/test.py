from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from .models import Post, Folder, SavedPost, Comment
import tempfile
from PIL import Image
import json


from django.contrib.auth import get_user_model

User = get_user_model()


class ModelTestCase(TestCase):
    """Test cases for models"""

    def setUp(self):
        """Set up test data"""
        self.user = User.objects.create_user(
            username='testuser', email='test1@email.com', password='password123')
        self.post = Post.objects.create(
            user=self.user,
            content='Test post content',
            visibility='public'
        )
        self.folder = Folder.objects.create(
            user=self.user,
            name='Test Folder'
        )
        self.saved_post = SavedPost.objects.create(
            user=self.user,
            post=self.post,
            folder=self.folder
        )

    def test_post_creation(self):
        """Test post creation and string representation"""
        self.assertEqual(self.post.content, 'Test post content')
        self.assertEqual(self.post.visibility, 'public')
        self.assertEqual(self.post.user, self.user)
        self.assertEqual(str(
            self.post), f"Post by {self.user.username} at {self.post.created_at.strftime('%Y-%m-%d %H:%M')}")

    def test_folder_creation(self):
        """Test folder creation and string representation"""
        self.assertEqual(self.folder.name, 'Test Folder')
        self.assertEqual(self.folder.user, self.user)
        self.assertEqual(str(self.folder),
                         f"Test Folder (by {self.user.username})")

    def test_saved_post_creation(self):
        """Test saved post creation and string representation"""
        self.assertEqual(self.saved_post.user, self.user)
        self.assertEqual(self.saved_post.post, self.post)
        self.assertEqual(self.saved_post.folder, self.folder)
        self.assertTrue("testuser saved post #" in str(self.saved_post))

    def test_post_validation(self):
        """Test post validation for empty content"""
        with self.assertRaises(ValueError):
            Post.objects.create(user=self.user, visibility='public')

    def test_unique_folder_constraint(self):
        """Test unique folder name constraint"""
        with self.assertRaises(Exception):  # Django will raise an integrity error
            # Same name as existing
            Folder.objects.create(user=self.user, name='Test Folder')

    def test_unique_saved_post_constraint(self):
        """Test unique saved post constraint"""
        with self.assertRaises(Exception):  # Django will raise an integrity error
            SavedPost.objects.create(
                user=self.user, post=self.post, folder=self.folder)  # Duplicate


class PostAPITestCase(APITestCase):
    """Test cases for Post API endpoints"""

    def setUp(self):
        """Set up test data"""
        self.user1 = User.objects.create_user(
            username='user1', email='test1@email.com', password='password123')
        self.user2 = User.objects.create_user(
            username='user2', email='test2@email.com', password='password123')

        self.client = APIClient()

        # Create test posts
        self.public_post = Post.objects.create(
            user=self.user1,
            content='Public post content',
            visibility='public'
        )

        self.private_post = Post.objects.create(
            user=self.user1,
            content='Private post content',
            visibility='private'
        )

    def test_get_public_posts_unauthenticated(self):
        """Test that unauthenticated users can see public posts but not private posts"""
        response = self.client.get(reverse('post-list'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = json.loads(response.content)
        self.assertEqual(len(data), 1)  # Only public post should be visible
        self.assertEqual(data[0]['content'], 'Public post content')

    def test_get_all_posts_authenticated_owner(self):
        """Test that authenticated post owners can see all their posts"""
        self.client.force_authenticate(user=self.user1)
        response = self.client.get(reverse('post-list'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = json.loads(response.content)
        self.assertEqual(len(data), 2)  # Both posts should be visible

    def test_get_only_public_posts_authenticated_non_owner(self):
        """Test that authenticated non-owners can only see public posts"""
        self.client.force_authenticate(user=self.user2)
        response = self.client.get(reverse('post-list'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = json.loads(response.content)
        self.assertEqual(len(data), 1)  # Only public post should be visible

    def test_create_post(self):
        """Test creating a new post"""
        self.client.force_authenticate(user=self.user1)
        data = {
            'content': 'New post content',
            'visibility': 'public'
        }
        response = self.client.post(reverse('post-list'), data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # Verify post was created
        self.assertEqual(Post.objects.count(), 3)
        self.assertEqual(Post.objects.latest(
            'created_at').content, 'New post content')

    def test_update_post_owner(self):
        """Test updating a post by its owner"""
        self.client.force_authenticate(user=self.user1)
        data = {'content': 'Updated content'}
        response = self.client.patch(
            reverse('post-detail', kwargs={'pk': self.public_post.id}),
            data
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Verify post was updated
        self.public_post.refresh_from_db()
        self.assertEqual(self.public_post.content, 'Updated content')

    def test_update_post_non_owner(self):
        """Test updating a post by a non-owner (should fail)"""
        self.client.force_authenticate(user=self.user2)
        data = {'content': 'Unauthorized update'}
        response = self.client.patch(
            reverse('post-detail', kwargs={'pk': self.public_post.id}),
            data
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        # Verify post was not updated
        self.public_post.refresh_from_db()
        self.assertEqual(self.public_post.content, 'Public post content')

    def test_delete_post_owner(self):
        """Test deleting a post by its owner"""
        self.client.force_authenticate(user=self.user1)
        response = self.client.delete(
            reverse('post-detail', kwargs={'pk': self.public_post.id})
        )
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        # Verify post was deleted
        self.assertEqual(Post.objects.count(), 1)

    def test_delete_post_non_owner(self):
        """Test deleting a post by a non-owner (should fail)"""
        self.client.force_authenticate(user=self.user2)
        response = self.client.delete(
            reverse('post-detail', kwargs={'pk': self.public_post.id})
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        # Verify post was not deleted
        self.assertEqual(Post.objects.count(), 2)

    def test_like_post(self):
        """Test liking a post"""
        self.client.force_authenticate(user=self.user2)
        response = self.client.post(
            reverse('post-like', kwargs={'pk': self.public_post.id})
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Verify like count increased
        self.public_post.refresh_from_db()
        self.assertEqual(self.public_post.like_count, 1)

    def test_unlike_post(self):
        """Test unliking a post"""
        # First like the post
        self.public_post.like_count = 1
        self.public_post.save()

        self.client.force_authenticate(user=self.user2)
        response = self.client.post(
            reverse('post-unlike', kwargs={'pk': self.public_post.id})
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Verify like count decreased
        self.public_post.refresh_from_db()
        self.assertEqual(self.public_post.like_count, 0)


    def test_share_post(self):
        """Test sharing a post"""
        self.client.force_authenticate(user=self.user2)
        response = self.client.post(
            reverse('post-share', kwargs={'pk': self.public_post.id})
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # Verify share count increased
        self.public_post.refresh_from_db()
        self.assertEqual(self.public_post.share_count, 1)

    def test_comment_on_post(self):
        """Test commenting on a post"""
        self.client.force_authenticate(user=self.user2)
        comment_data = {
            'content': 'This is a test comment.'
        }
        response = self.client.post(
            reverse('post-comment', kwargs={'pk': self.public_post.id}),
            data=comment_data
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # Verify comment count increased
        self.public_post.refresh_from_db()
        self.assertEqual(self.public_post.comment_count, 1)

        # Verify the content of the comment
        self.assertEqual(self.public_post.comments.last().content, 'This is a test comment.')


    def test_delete_comment(self):
        """Test deleting a comment"""
        # Authenticate as the comment owner (user2)
        self.client.force_authenticate(user=self.user2)

        # Delete the comment
        response = self.client.delete(
            reverse('post-delete-comment', kwargs={'pk': self.public_post.id}),
            data={'comment_id': self.comment.id}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Verify the comment is deleted
        self.assertFalse(Comment.objects.filter(id=self.comment.id).exists())

        # Verify the comment count on the post is decremented
        self.public_post.refresh_from_db()
        self.assertEqual(self.public_post.comment_count, 0)

    def test_delete_comment_as_admin(self):
        """Test deleting a comment as an admin"""
        # Create an admin user
        admin_user = User.objects.create_user(username='admin', password='admin123', is_staff=True)
        self.client.force_authenticate(user=admin_user)

        # Delete the comment
        response = self.client.delete(
            reverse('post-delete-comment', kwargs={'pk': self.public_post.id}),
            data={'comment_id': self.comment.id}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Verify the comment is deleted
        self.assertFalse(Comment.objects.filter(id=self.comment.id).exists())

        # Verify the comment count on the post is decremented
        self.public_post.refresh_from_db()
        self.assertEqual(self.public_post.comment_count, 0)

    def test_delete_comment_unauthorized(self):
        """Test deleting a comment as a non-owner/non-admin"""
        # Authenticate as a different user (user1, who is not the comment owner)
        self.client.force_authenticate(user=self.user1)

        # Attempt to delete the comment
        response = self.client.delete(
            reverse('post-delete-comment', kwargs={'pk': self.public_post.id}),
            data={'comment_id': self.comment.id}
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        # Verify the comment still exists
        self.assertTrue(Comment.objects.filter(id=self.comment.id).exists())

        # Verify the comment count on the post remains unchanged
        self.public_post.refresh_from_db()
        self.assertEqual(self.public_post.comment_count, 1)

    def test_delete_comment_with_replies(self):
        """Test deleting a comment that has replies"""
        # Create a reply to the comment
        reply = Comment.objects.create(user=self.user1, post=self.public_post, content="This is a reply", parent=self.comment)

        # Authenticate as the comment owner (user2)
        self.client.force_authenticate(user=self.user2)

        # Delete the parent comment
        response = self.client.delete(
            reverse('post-delete-comment', kwargs={'pk': self.public_post.id}),
            data={'comment_id': self.comment.id}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Verify the parent comment and its reply are deleted
        self.assertFalse(Comment.objects.filter(id=self.comment.id).exists())
        self.assertFalse(Comment.objects.filter(id=reply.id).exists())

        # Verify the comment count on the post is decremented
        self.public_post.refresh_from_db()
        self.assertEqual(self.public_post.comment_count, 0)


class FolderAPITestCase(APITestCase):
    """Test cases for Folder API endpoints"""

    def setUp(self):
        """Set up test data"""
        self.user1 = User.objects.create_user(
            username='user1', email='test1@email.com', password='password123')
        self.user2 = User.objects.create_user(
            username='user2', email='test2@email.com', password='password123')

        self.client = APIClient()

        # Create test folders
        self.folder1 = Folder.objects.create(
            user=self.user1,
            name='Folder 1'
        )

        self.folder2 = Folder.objects.create(
            user=self.user2,
            name='Folder 2'
        )

    def test_list_own_folders(self):
        """Test that users can only list their own folders"""
        self.client.force_authenticate(user=self.user1)
        response = self.client.get(reverse('folder-list'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = json.loads(response.content)
        self.assertEqual(len(data), 1)  # Only user1's folder
        self.assertEqual(data[0]['name'], 'Folder 1')

    def test_create_folder(self):
        """Test creating a new folder"""
        self.client.force_authenticate(user=self.user1)
        data = {'name': 'New Folder'}
        response = self.client.post(reverse('folder-list'), data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # Verify folder was created
        self.assertEqual(Folder.objects.filter(user=self.user1).count(), 2)
        self.assertTrue(Folder.objects.filter(
            user=self.user1, name='New Folder').exists())

    def test_create_duplicate_folder(self):
        """Test creating a folder with a duplicate name (should fail)"""
        self.client.force_authenticate(user=self.user1)
        data = {'name': 'Folder 1'}  # Same name as existing folder
        response = self.client.post(reverse('folder-list'), data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        # Verify no new folder was created
        self.assertEqual(Folder.objects.filter(user=self.user1).count(), 1)

    def test_update_folder_owner(self):
        """Test updating a folder by its owner"""
        self.client.force_authenticate(user=self.user1)
        data = {'name': 'Updated Folder'}
        response = self.client.patch(
            reverse('folder-detail', kwargs={'pk': self.folder1.id}),
            data
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Verify folder was updated
        self.folder1.refresh_from_db()
        self.assertEqual(self.folder1.name, 'Updated Folder')

    def test_update_folder_non_owner(self):
        """Test updating a folder by a non-owner (should fail)"""
        self.client.force_authenticate(user=self.user2)
        data = {'name': 'Unauthorized update'}
        response = self.client.patch(
            reverse('folder-detail', kwargs={'pk': self.folder1.id}),
            data
        )
        # Should not be visible to non-owner
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

        # Verify folder was not updated
        self.folder1.refresh_from_db()
        self.assertEqual(self.folder1.name, 'Folder 1')

    def test_delete_folder_owner(self):
        """Test deleting a folder by its owner"""
        self.client.force_authenticate(user=self.user1)
        response = self.client.delete(
            reverse('folder-detail', kwargs={'pk': self.folder1.id})
        )
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        # Verify folder was deleted
        self.assertFalse(Folder.objects.filter(id=self.folder1.id).exists())


class SavedPostAPITestCase(APITestCase):
    """Test cases for SavedPost API endpoints"""

    def setUp(self):
        """Set up test data"""
        self.user1 = User.objects.create_user(
            username='user1', email='test1@email.com', password='password123')
        self.user2 = User.objects.create_user(
            username='user2', email='test2@email.com', password='password123')

        self.client = APIClient()

        # Create test posts
        self.post1 = Post.objects.create(
            user=self.user1,
            content='Post 1 content',
            visibility='public'
        )

        self.post2 = Post.objects.create(
            user=self.user2,
            content='Post 2 content',
            visibility='public'
        )

        # Create test folders
        self.folder1 = Folder.objects.create(
            user=self.user1,
            name='Folder 1'
        )

        # Create test saved posts
        self.saved_post1 = SavedPost.objects.create(
            user=self.user1,
            post=self.post2,
            folder=self.folder1
        )

        self.saved_post2 = SavedPost.objects.create(
            user=self.user1,
            post=self.post1,
            folder=None  # No folder
        )

    def test_list_saved_posts(self):
        """Test listing saved posts"""
        self.client.force_authenticate(user=self.user1)
        response = self.client.get(reverse('saved-post-list'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = json.loads(response.content)
        self.assertEqual(len(data), 2)  # Both saved posts

    def test_list_saved_posts_by_folder(self):
        """Test listing saved posts filtered by folder"""
        self.client.force_authenticate(user=self.user1)
        response = self.client.get(
            f"{reverse('saved-post-list')}?folder_id={self.folder1.id}")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = json.loads(response.content)
        self.assertEqual(len(data), 1)  # Only one post in the folder
        self.assertEqual(data[0]['post']['id'], self.post2.id)

    def test_list_unfiled_saved_posts(self):
        """Test listing saved posts that are not in any folder"""
        self.client.force_authenticate(user=self.user1)
        response = self.client.get(
            f"{reverse('saved-post-list')}?folder_id=null")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = json.loads(response.content)
        self.assertEqual(len(data), 1)  # Only one post not in a folder
        self.assertEqual(data[0]['post']['id'], self.post1.id)

    def test_toggle_save_post(self):
        """Test toggling post save status (save new post)"""
        self.client.force_authenticate(user=self.user2)
        data = {'post_id': self.post1.id}
        response = self.client.post(reverse('saved-post-toggle-save'), data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # Verify post was saved
        self.assertTrue(SavedPost.objects.filter(
            user=self.user2, post=self.post1).exists())

    def test_toggle_unsave_post(self):
        """Test toggling post save status (unsave existing post)"""
        self.client.force_authenticate(user=self.user1)
        data = {'post_id': self.post2.id, 'folder_id': self.folder1.id}
        response = self.client.post(reverse('saved-post-toggle-save'), data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Verify post was unsaved
        self.assertFalse(SavedPost.objects.filter(
            id=self.saved_post1.id).exists())

    def test_save_to_specific_folder(self):
        """Test saving a post to a specific folder"""
        # Create another folder
        folder2 = Folder.objects.create(user=self.user1, name='Folder 2')

        self.client.force_authenticate(user=self.user1)
        data = {'post_id': self.post2.id, 'folder_id': folder2.id}
        response = self.client.post(reverse('saved-post-list'), data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # Verify post was saved to the new folder
        self.assertTrue(SavedPost.objects.filter(
            user=self.user1, post=self.post2, folder=folder2).exists())

    def test_no_duplicate_saves(self):
        """Test that a post cannot be saved to the same folder twice"""
        self.client.force_authenticate(user=self.user1)
        data = {'post_id': self.post2.id, 'folder_id': self.folder1.id}
        response = self.client.post(reverse('saved-post-list'), data)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        # Count should still be just one in this folder
        self.assertEqual(SavedPost.objects.filter(
            user=self.user1, post=self.post2, folder=self.folder1
        ).count(), 1)



class ProfileAndPostPermissionTestCase(APITestCase):
    """Test cases for viewing user profiles and posts with permission"""

    def setUp(self):
        """Set up test data"""
        self.user1 = User.objects.create_user(
            username='user1', email='user1@email.com', password='password123')
        self.user2 = User.objects.create_user(
            username='user2', email='user2@email.com', password='password123')

        self.client = APIClient()

        # Create test posts for user1
        self.public_post = Post.objects.create(
            user=self.user1,
            content='This is a public post.',
            visibility='public'
        )

        self.private_post = Post.objects.create(
            user=self.user1,
            content='This is a private post.',
            visibility='private'
        )

    def test_view_public_profile_unauthenticated(self):
        """Test that unauthenticated users can view public user profiles"""
        response = self.client.get(reverse('user-profile', kwargs={'username': self.user1.username}))
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Ensure only public profile details are visible
        data = json.loads(response.content)
        self.assertIn('username', data)
        self.assertNotIn('email', data)  # Email should not be exposed

    def test_view_profile_authenticated(self):
        """Test that authenticated users can view other users' profiles"""
        self.client.force_authenticate(user=self.user2)
        response = self.client.get(reverse('user-profile', kwargs={'username': self.user1.username}))
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = json.loads(response.content)
        self.assertIn('username', data)
        self.assertNotIn('email', data)  # Sensitive information should be hidden

    def test_view_public_posts_authenticated(self):
        """Test that authenticated users can see public posts of others"""
        self.client.force_authenticate(user=self.user2)
        response = self.client.get(reverse('user-posts', kwargs={'username': self.user1.username}))
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = json.loads(response.content)
        self.assertEqual(len(data), 1)  # Only public posts should be visible
        self.assertEqual(data[0]['content'], 'This is a public post.')

    def test_view_private_posts_authenticated(self):
        """Test that authenticated users cannot see private posts of others"""
        self.client.force_authenticate(user=self.user2)
        response = self.client.get(reverse('user-posts', kwargs={'username': self.user1.username}))
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = json.loads(response.content)
        self.assertEqual(len(data), 1)  # Only public posts should be visible
        self.assertNotIn('This is a private post.', [post['content'] for post in data])

    def test_view_own_private_posts(self):
        """Test that users can view their own private posts"""
        self.client.force_authenticate(user=self.user1)
        response = self.client.get(reverse('user-posts', kwargs={'username': self.user1.username}))
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = json.loads(response.content)
        self.assertEqual(len(data), 2)  # Both public and private posts should be visible

    def test_view_non_existent_user_profile(self):
        """Test that accessing a non-existent user profile returns 404"""
        self.client.force_authenticate(user=self.user2)
        response = self.client.get(reverse('user-profile', kwargs={'username': 'nonexistentuser'}))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
