from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from .models import Post, Folder, SavedPost, Comment, Like, Share, Tag
import tempfile
from PIL import Image
import json
from django.utils import timezone
from datetime import timedelta


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
            visibility='public',
            disclaimer='Fictional interpretation'
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


class PostDisclaimerTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='user1', password='password1')
        self.client.login(username='user1', password='password1')
        self.post = Post.objects.create(user=self.user, content="Test Post", disclaimer="Fictional interpretation")
        self.post_data = {'content': 'New post with disclaimer', 'disclaimer': 'Fictional interpretation'}
    
    def test_create_post_with_disclaimer(self):
        response = self.client.post('/content/posts/', self.post_data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['disclaimer'], 'Fictional interpretation')
    
    def test_update_post_with_disclaimer(self):
        update_data = {'disclaimer': 'Notes contain AI-generated content'}
        response = self.client.patch(f'/content/posts/{self.post.id}/', update_data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.post.refresh_from_db()
        self.assertEqual(self.post.disclaimer, 'Notes contain AI-generated content')
    
    def test_view_post_with_disclaimer(self):
        response = self.client.get(f'/content/posts/{self.post.id}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['disclaimer'], 'Fictional interpretation')
    
    def test_create_post_without_disclaimer(self):
        post_data_no_disclaimer = {'content': 'Another test post content', 'visibility': 'public'}
        response = self.client.post('/content/posts/', post_data_no_disclaimer)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertNotIn('disclaimer', response.data)
    
    def test_update_post_to_empty_disclaimer(self):
        update_data = {'disclaimer': ''}
        response = self.client.patch(f'/content/posts/{self.post.id}/', update_data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.post.refresh_from_db()
        self.assertEqual(self.post.disclaimer, '')


class PostVisibilityTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='user1', password='password1')
        self.client.login(username='user1', password='password1')
        self.post = Post.objects.create(user=self.user, content="Test Post", visibility="public")
    
    def test_create_post_with_visibility(self):
        data = {'content': 'New test post', 'visibility': 'private'}
        response = self.client.post('/posts/', data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['visibility'], 'private')
    
    def test_edit_post_visibility(self):
        update_data = {'visibility': 'friends'}
        response = self.client.patch(f'/posts/{self.post.id}/update_visibility/', update_data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.post.refresh_from_db()
        self.assertEqual(self.post.visibility, 'friends')
    
    def test_unauthorized_edit_visibility(self):
        new_user = User.objects.create_user(username='otheruser', password='password123')
        self.client.force_authenticate(user=new_user)
        response = self.client.patch(f'/posts/{self.post.id}/update_visibility/', {'visibility': 'private'})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class PostInteractionViewSetTests(APITestCase):
    def setUp(self):
        self.user1 = User.objects.create_user(username='user1', password='password1')
        self.user2 = User.objects.create_user(username='user2', password='password2')
        self.post = Post.objects.create(user=self.user1, content="Test Post")
        self.client.login(username='user1', password='password1')
    
    def test_list_likes(self):
        Like.objects.create(post=self.post, user=self.user2)
        response = self.client.get(f'/api/posts/{self.post.id}/interactions/likes/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['username'], 'user2')
    
    def test_list_shares(self):
        Share.objects.create(post=self.post, user=self.user2)
        response = self.client.get(f'/api/posts/{self.post.id}/interactions/shares/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['username'], 'user2')
    
    def test_list_comments(self):
        Comment.objects.create(post=self.post, user=self.user2, content="Nice post!")
        response = self.client.get(f'/api/posts/{self.post.id}/interactions/comments/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['username'], 'user2')
        self.assertEqual(response.data[0]['content'], "Nice post!")
    
    def test_no_interactions(self):
        response_likes = self.client.get(f'/api/posts/{self.post.id}/interactions/likes/')
        response_shares = self.client.get(f'/api/posts/{self.post.id}/interactions/shares/')
        response_comments = self.client.get(f'/api/posts/{self.post.id}/interactions/comments/')
        self.assertEqual(response_likes.status_code, status.HTTP_200_OK)
        self.assertEqual(response_shares.status_code, status.HTTP_200_OK)
        self.assertEqual(response_comments.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response_likes.data), 0)
        self.assertEqual(len(response_shares.data), 0)
        self.assertEqual(len(response_comments.data), 0)



class PostCaptionAndTagsTestCase(APITestCase):
    """Test cases for post captions and tags functionality"""

    def setUp(self):
        """Set up test data"""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

        self.existing_tag = Tag.objects.create(name='existingtag')

        self.valid_post_data = {
            'content': 'Test post content',
            'caption': 'This is a test caption',
            'tags': ['testtag1', 'testtag2', 'existingtag'],
            'visibility': 'public'
        }

    def test_create_post_with_caption_and_tags(self):
        """Test creating a post with caption and tags"""
        response = self.client.post(
            reverse('post-list'),
            data=self.valid_post_data,
            format='json'
        )

        if response.status_code == 404:
            print("Endpoint not found. Check your URL configuration.")
            print("Attempted URL:", reverse('post-list'))

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        if 'caption' not in response.data:
            print("Unexpected response structure:", response.data)

        # Check caption was saved
        self.assertEqual(response.data['caption'], 'This is a test caption')
        
        # Check tags were saved and properly serialized
        self.assertEqual(len(response.data['tags']), 3)
        tag_names = [tag['name'] for tag in response.data['tags']]
        self.assertIn('testtag1', tag_names)
        self.assertIn('testtag2', tag_names)
        self.assertIn('existingtag', tag_names)

    def test_create_post_with_long_caption(self):
        """Test caption length validation"""
        long_caption = 'x' * 301  # Exceeds 300 character limit
        post_data = {
            'content': 'Test content',
            'caption': long_caption,
            'visibility': 'public'
        }
        response = self.client.post(
            reverse('post-list'),
            data=post_data,
            format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('caption', response.data)
        self.assertEqual(
            response.data['caption'][0],
            "Caption cannot exceed 300 characters"
        )

    def test_create_post_with_too_many_tags(self):
        """Test tag count validation"""
        post_data = {
            'content': 'Test content',
            'tags': [f'tag{i}' for i in range(11)],  # 11 tags (limit is 10)
            'visibility': 'public'
        }
        response = self.client.post(
            reverse('post-list'),
            data=post_data,
            format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('tags', response.data)
        self.assertEqual(
            response.data['tags'][0],
            "Cannot add more than 10 tags to a post"
        )

    def test_view_post_with_caption_and_tags(self):
        """Test viewing a post with caption and tags"""

        create_response = self.client.post(
            reverse('post-list'),
            data=self.valid_post_data,
            format='json'
        )
        post_id = create_response.data['id']

        retrieve_response = self.client.get(
            reverse('post-detail', kwargs={'pk': post_id})
        )
        self.assertEqual(retrieve_response.status_code, status.HTTP_200_OK)
        
        # Verify caption and tags are displayed
        self.assertEqual(
            retrieve_response.data['caption'],
            'This is a test caption'
        )
        self.assertEqual(len(retrieve_response.data['tags']), 3)

    def test_update_post_caption_and_tags(self):
        """Test updating a post's caption and tags"""

        create_response = self.client.post(
            reverse('post-list'),
            data=self.valid_post_data,
            format='json'
        )
        post_id = create_response.data['id']

        update_data = {
            'caption': 'Updated caption',
            'tags': ['updatedtag1', 'updatedtag2']
        }
        update_response = self.client.patch(
            reverse('post-detail', kwargs={'pk': post_id}),
            data=update_data,
            format='json'
        )
        self.assertEqual(update_response.status_code, status.HTTP_200_OK)
        
        # Verify the updates
        self.assertEqual(update_response.data['caption'], 'Updated caption')
        tag_names = [tag['name'] for tag in update_response.data['tags']]
        self.assertEqual(len(tag_names), 2)
        self.assertIn('updatedtag1', tag_names)
        self.assertIn('updatedtag2', tag_names)

    def test_remove_caption_and_tags(self):
        """Test removing caption and tags from a post"""

        create_response = self.client.post(
            reverse('post-list'),
            data=self.valid_post_data,
            format='json'
        )
        post_id = create_response.data['id']

        # Remove caption and tags
        update_data = {
            'caption': '',
            'tags': []
        }
        update_response = self.client.patch(
            reverse('post-detail', kwargs={'pk': post_id}),
            data=update_data,
            format='json'
        )
        self.assertEqual(update_response.status_code, status.HTTP_200_OK)
        
        # Verify the removal
        self.assertEqual(update_response.data['caption'], '')
        self.assertEqual(len(update_response.data['tags']), 0)

    def test_create_post_with_duplicate_tags(self):
        """Test that duplicate tags are handled properly"""
        post_data = {
            'content': 'Test content',
            'tags': ['duptag', 'duptag', 'DUPTAG'],  # Different case duplicates
            'visibility': 'public'
        }
        response = self.client.post(
            reverse('post-list'),
            data=post_data,
            format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        # Should only create one tag instance
        self.assertEqual(len(response.data['tags']), 1)
        self.assertEqual(response.data['tags'][0]['name'], 'duptag')

    def test_create_post_with_invalid_tag_characters(self):
        """Test that invalid tag characters are rejected"""
        post_data = {
            'content': 'Test content',
            'tags': ['valid', 'invalid!tag', 'another@tag'],
            'visibility': 'public'
        }
        response = self.client.post(
            reverse('post-list'),
            data=post_data,
            format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('tags', response.data)

    def test_search_posts_by_tag(self):
        """Test searching posts by tag"""
        # Create posts with different tags
        self.client.post(
            reverse('post-list'),
            data={
                'content': 'Post with tag1',
                'tags': ['tag1'],
                'visibility': 'public'
            },
            format='json'
        )
        self.client.post(
            reverse('post-list'),
            data={
                'content': 'Post with tag2',
                'tags': ['tag2'],
                'visibility': 'public'
            },
            format='json'
        )

        # Search by tag1
        response = self.client.get(
            reverse('post-by-tag') + '?name=tag1'
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['content'], 'Post with tag1')


class PostSchedulingTestCase(APITestCase):
    """Test cases for Post Scheduling functionality"""

    def setUp(self):
        """Set up test data"""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@email.com',
            password='password123'
        )
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

        # Create test posts
        self.published_post = Post.objects.create(
            user=self.user,
            content='Published post',
            status='published'
        )

        self.draft_post = Post.objects.create(
            user=self.user,
            content='Draft post',
            status='draft'
        )

        self.scheduled_post = Post.objects.create(
            user=self.user,
            content='Scheduled post',
            status='draft',
            is_scheduled=True,
            scheduled_time=timezone.now() + timedelta(days=1)
        )

    def test_create_scheduled_post(self):
        """Test creating a new scheduled post"""
        post_data = {
            'content': 'New scheduled post',
            'is_scheduled': True,
            'scheduled_time': (timezone.now() + timedelta(hours=1)).isoformat(),
            'status': 'draft'
        }
        response = self.client.post(
            reverse('post-list'),
            data=post_data,
            format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(response.data['is_scheduled'])
        self.assertEqual(response.data['status'], 'draft')

    def test_create_invalid_scheduled_post(self):
        """Test creating a scheduled post with invalid data"""
        # Past scheduled time
        post_data = {
            'content': 'Invalid scheduled post',
            'is_scheduled': True,
            'scheduled_time': (timezone.now() - timedelta(hours=1)).isoformat()
        }
        response = self.client.post(
            reverse('post-list'),
            data=post_data,
            format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('scheduled_time', response.data)

    def test_list_scheduled_posts(self):
        """Test listing scheduled posts"""
        response = self.client.get(reverse('post-scheduled'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = json.loads(response.content)
        self.assertEqual(len(data['results']), 1)
        self.assertEqual(data['results'][0]['id'], self.scheduled_post.id)

    def test_cancel_scheduled_post(self):
        """Test canceling a scheduled post"""
        response = self.client.post(
            reverse('post-cancel-schedule', kwargs={'pk': self.scheduled_post.id})
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Refresh from db
        self.scheduled_post.refresh_from_db()
        self.assertFalse(self.scheduled_post.is_scheduled)
        self.assertIsNone(self.scheduled_post.scheduled_time)

    def test_cancel_non_scheduled_post(self):
        """Test canceling a post that isn't scheduled"""
        response = self.client.post(
            reverse('post-cancel-schedule', kwargs={'pk': self.published_post.id})
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_edit_scheduled_post(self):
        """Test editing a scheduled post"""
        new_time = timezone.now() + timedelta(hours=2)
        response = self.client.patch(
            reverse('post-detail', kwargs={'pk': self.scheduled_post.id}),
            data={
                'scheduled_time': new_time.isoformat(),
                'content': 'Updated content'
            },
            format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Refresh from db
        self.scheduled_post.refresh_from_db()
        self.assertEqual(
            self.scheduled_post.scheduled_time.replace(tzinfo=None),
            new_time.replace(tzinfo=None)
        )
        self.assertEqual(self.scheduled_post.content, 'Updated content')

    def test_publish_scheduled_post_early(self):
        """Test manually publishing a scheduled post"""
        response = self.client.patch(
            reverse('post-detail', kwargs={'pk': self.scheduled_post.id}),
            data={
                'status': 'published',
                'is_scheduled': False,
                'scheduled_time': None
            },
            format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Refresh from db
        self.scheduled_post.refresh_from_db()
        self.assertEqual(self.scheduled_post.status, 'published')
        self.assertFalse(self.scheduled_post.is_scheduled)

    def test_scheduled_post_visibility(self):
        """Test scheduled posts aren't visible in regular listings"""
        response = self.client.get(reverse('post-list'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        data = json.loads(response.content)
        post_ids = [post['id'] for post in data['results']]
        self.assertNotIn(self.scheduled_post.id, post_ids)