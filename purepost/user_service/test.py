import json
from django.urls import reverse
from rest_framework.test import APITestCase
from rest_framework import status
from django.contrib.auth import get_user_model
from rest_framework.authtoken.models import Token
from .models import Profile

User = get_user_model()


class ProfileTests(APITestCase):
    def setUp(self) -> None:
        """
        Set up test data, including two test users, their profiles, and authentication tokens.
        """
        # Create test users
        self.user1 = User.objects.create_user(username="testuser1", email="user1@example.com", password="password123")
        self.user2 = User.objects.create_user(username="testuser2", email="user2@example.com", password="password123")

        # Create authentication tokens for the users
        self.token1 = Token.objects.create(user=self.user1)
        self.token2 = Token.objects.create(user=self.user2)

        # Create profiles for the test users
        self.profile1 = Profile.objects.create(user=self.user1, bio="This is user1's bio.", location="Earth")
        self.profile2 = Profile.objects.create(user=self.user2, bio="This is user2's bio.", location="Mars")

        # URLs
        self.public_profile_url = reverse("profile-detail", kwargs={"username": self.user1.username})
        self.my_profile_url = reverse("my-profile")
        self.update_profile_url = reverse("update-profile")

    def test_retrieve_public_profile(self) -> None:
        """
        Test that a public user's profile can be retrieved by username.
        """
        response = self.client.get(self.public_profile_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["bio"], "This is user1's bio.")
        self.assertEqual(response.data["location"], "Earth")

    def test_retrieve_logged_in_user_profile(self) -> None:
        """
        Test that an authenticated user can retrieve their own profile.
        """
        # Authenticate using the token for user1
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {self.token1.key}")
        response = self.client.get(self.my_profile_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["bio"], "This is user1's bio.")
        self.assertEqual(response.data["location"], "Earth")

    def test_retrieve_logged_in_user_profile_unauthenticated(self) -> None:
        """
        Test that accessing the logged-in user's profile without authentication fails.
        """
        response = self.client.get(self.my_profile_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_update_profile(self) -> None:
        """
        Test that an authenticated user can update their own profile.
        """
        # Authenticate using the token for user1
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {self.token1.key}")
        new_data = {
            "bio": "Updated bio for user1.",
            "location": "Updated location."
        }
        response = self.client.put(self.update_profile_url, data=json.dumps(new_data), content_type="application/json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["bio"], "Updated bio for user1.")
        self.assertEqual(response.data["location"], "Updated location.")

    def test_update_profile_unauthenticated(self) -> None:
        """
        Test that updating a profile without authentication fails.
        """
        new_data = {
            "bio": "Unauthorized update.",
            "location": "Unauthorized location."
        }
        response = self.client.put(self.update_profile_url, data=json.dumps(new_data), content_type="application/json")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_profile_detail_not_found(self) -> None:
        """
        Test that trying to retrieve a profile for a non-existent username returns 404.
        """
        response = self.client.get(reverse("profile-detail", kwargs={"username": "nonexistent"}))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)