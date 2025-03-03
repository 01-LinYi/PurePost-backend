from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from .models import Post, Folder, SavedPost

User = get_user_model()


class ContentModerationTests(APITestCase):
    
    def setUp(self):
        """Set up users and initial posts."""
        self.user1 = User.objects.create_user(username="user1", password="password123")
        self.user2 = User.objects.create_user(username="user2", password="password123")
        
        self.client1 = APIClient()
        self.client2 = APIClient()
        self.client1.force_authenticate(user=self.user1)
        self.client2.force_authenticate(user=self.user2)

        # Create a sample post by user1
        self.post = Post.objects.create(user=self.user1, content="Original post")
        
        # Create a folder for testing
        self.folder = Folder.objects.create(user=self.user1, name="My Folder")

        print("Created Post:", Post.objects.all())
        print("Created Folder:", Folder.objects.all())


    def test_create_post(self):
        """Test that a user can create a post."""
        data = {"content": "New post", "media": ""}
        response = self.client1.post("/api/posts/", data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Post.objects.count(), 2)

    def test_edit_post(self):
        """Test that only the post creator can edit."""
        edit_data = {"content": "Updated content"}
        
        # User1 edits their own post
        response = self.client1.put(f"/api/posts/{self.post.id}/", edit_data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.post.refresh_from_db()
        self.assertEqual(self.post.content, "Updated content")
        
        # User2 tries to edit User1's post
        response = self.client2.put(f"/api/posts/{self.post.id}/", edit_data)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_delete_post(self):
        """Test that only the post creator can delete."""
        # User1 deletes their own post
        response = self.client1.delete(f"/api/posts/{self.post.id}/")
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(Post.objects.count(), 0)

        # User2 tries to delete User1's post
        new_post = Post.objects.create(user=self.user1, content="Another post")
        response = self.client2.delete(f"/api/posts/{new_post.id}/")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_create_folder(self):
        """Test that a user can create a folder."""
        data = {"name": "New Folder"}
        response = self.client1.post("/api/folders/", data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Folder.objects.count(), 2)

    def test_edit_folder(self):
        """Test that a user can edit their own folder."""
        edit_data = {"name": "Updated Folder"}
        response = self.client1.put(f"/api/folders/{self.folder.id}/", edit_data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.folder.refresh_from_db()
        self.assertEqual(self.folder.name, "Updated Folder")

        # User2 tries to edit User1's folder
        response = self.client2.put(f"/api/folders/{self.folder.id}/", edit_data)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_delete_folder(self):
        """Test that only the folder creator can delete."""
        response = self.client1.delete(f"/api/folders/{self.folder.id}/")
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(Folder.objects.count(), 0)

        # User2 tries to delete User1's folder
        new_folder = Folder.objects.create(user=self.user1, name="Another Folder")
        response = self.client2.delete(f"/api/folders/{new_folder.id}/")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_save_post_to_folder(self):
        """Test that a user can save a post to a folder."""
        data = {"post_id": self.post.id, "folder_id": self.folder.id}
        response = self.client1.post("/api/saved-posts/", data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(SavedPost.objects.count(), 1)

    def test_fetch_posts_by_folder(self):
        """Test that a user can retrieve posts in a folder."""
        SavedPost.objects.create(folder=self.folder, post=self.post, user=self.user1)
        response = self.client1.get(f"/api/saved-posts/?folder_id={self.folder.id}")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
