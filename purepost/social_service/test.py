from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
import pdb

from purepost.social_service.models import Follow, Block

User = get_user_model()


class FollowModelTests(TestCase):
    """Test the Follow model functionality"""

    def setUp(self):
        self.user1 = User.objects.create_user(
            username='user1',
            email='user1@example.com',
            password='password1'
        )
        self.user2 = User.objects.create_user(
            username='user2',
            email='user2@example.com',
            password='password2'
        )
        self.user3 = User.objects.create_user(
            username='user3',
            email='user3@example.com',
            password='password3'
        )

    def test_follow_unfollow(self):
        # Test creating a follow
        follow_obj, created = Follow.follow(self.user1, self.user2)
        self.assertTrue(created)
        self.assertTrue(follow_obj.is_active)
        self.assertEqual(follow_obj.follower, self.user1)
        self.assertEqual(follow_obj.following, self.user2)

        # Test follow count
        self.assertEqual(Follow.get_follower_count(self.user2), 1)
        self.assertEqual(Follow.get_following_count(self.user1), 1)

        # Test is_following function
        self.assertTrue(Follow.is_following(self.user1, self.user2))
        self.assertFalse(Follow.is_following(self.user2, self.user1))

        # Test unfollow
        result = Follow.unfollow(self.user1, self.user2)
        self.assertTrue(result)

        # Check state after unfollow
        self.assertFalse(Follow.is_following(self.user1, self.user2))
        self.assertEqual(Follow.get_follower_count(self.user2), 0)

        # Test unfollowing non-followed user
        result = Follow.unfollow(self.user1, self.user3)
        self.assertFalse(result)

    def test_cannot_follow_self(self):
        # Test that users cannot follow themselves
        with self.assertRaises(ValueError):
            Follow.follow(self.user1, self.user1)


class BlockModelTests(TestCase):
    """Test the Block model functionality"""

    def setUp(self):
        self.user1 = User.objects.create_user(
            username='user1',
            email='user1@example.com',
            password='password1'
        )
        self.user2 = User.objects.create_user(
            username='user2',
            email='user2@example.com',
            password='password2'
        )

        # Create initial follow relationships
        Follow.follow(self.user1, self.user2)
        Follow.follow(self.user2, self.user1)

    def test_block_unblock(self):
        # Test blocking a user
        block_obj, created = Block.block_user(
            self.user1, self.user2, "Test reason")
        self.assertTrue(created)
        self.assertEqual(block_obj.blocker, self.user1)
        self.assertEqual(block_obj.blocked, self.user2)
        self.assertEqual(block_obj.reason, "Test reason")

        # Verify follows are deactivated
        self.assertFalse(Follow.is_following(self.user1, self.user2))
        self.assertFalse(Follow.is_following(self.user2, self.user1))

        # Test is_blocked
        self.assertTrue(Block.is_blocked(self.user1, self.user2))
        self.assertFalse(Block.is_blocked(self.user2, self.user1))

        # Test unblocking
        result = Block.unblock_user(self.user1, self.user2)
        self.assertTrue(result)
        self.assertFalse(Block.is_blocked(self.user1, self.user2))

        # Test unblocking a user who isn't blocked
        result = Block.unblock_user(self.user1, self.user2)
        self.assertFalse(result)

    def test_cannot_block_self(self):
        with self.assertRaises(ValueError):
            Block.block_user(self.user1, self.user1)


class FollowAPITests(APITestCase):
    """Test the Follow API endpoints"""

    def setUp(self):
        self.user1 = User.objects.create_user(
            username='user1',
            email='user1@example.com',
            password='password1'
        )
        self.user2 = User.objects.create_user(
            username='user2',
            email='user2@example.com',
            password='password2'
        )
        self.user3 = User.objects.create_user(
            username='user3',
            email='user3@example.com',
            password='password3'
        )

        self.client = APIClient()

        # Create some follow relationships
        Follow.follow(self.user2, self.user1)  # user2 follows user1
        Follow.follow(self.user3, self.user1)  # user3 follows user1
        Follow.follow(self.user1, self.user3)  # user1 follows user3

    def test_authentication_required(self):
        # Ensure client is not authenticated
        self.client.force_authenticate(user=None)
        
        # Try to follow a user without authentication
        url = reverse('follow-user', kwargs={'user_id': self.user2.id})
        response = self.client.post(url)
        
        # Check that we get 401 Unauthorized
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_follow_user(self):
        # Login as user1
        self.client.force_authenticate(user=self.user1)

        # Follow user2
        url = reverse('follow-user', kwargs={'user_id': self.user2.id})
        response = self.client.post(url)

        # Check response
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # Verify the follow relationship
        self.assertTrue(Follow.is_following(self.user1, self.user2))

    def test_unfollow_user(self):
        # Login as user1
        self.client.force_authenticate(user=self.user1)

        # First follow user2
        Follow.follow(self.user1, self.user2)

        # Unfollow user2
        url = reverse('unfollow-user', kwargs={'user_id': self.user2.id})
        response = self.client.delete(url)

        # Check response
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        # Verify the follow relationship is removed
        self.assertFalse(Follow.is_following(self.user1, self.user2))


    def test_follow_status(self):
        # Login as user1
        self.client.force_authenticate(user=self.user1)
        
        # Get follow status for user1
        url = reverse('follow-status')
        response = self.client.get(url)
        
        # Check response
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        
        # Check response structure
        self.assertTrue(isinstance(response.data, dict), "Response should be a dictionary")
        
        # Check if the expected fields exist
        self.assertIn('is_following', response.data, "is_following field missing")
        self.assertIn('follower_count', response.data, "follower_count field missing")
        self.assertIn('following_count', response.data, "following_count field missing")
        
        # Check values
        self.assertEqual(response.data['follower_count'], 2)  # user2 and user3 follow user1
        self.assertEqual(response.data['following_count'], 1)  # user1 follows user3
        

        # Get follow status for user2
        url = reverse('user-follow-status', kwargs={'user_id': self.user2.id})
        response = self.client.get(url)

        # Check response
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Nobody follows user2 yet
        self.assertEqual(response.data['follower_count'], 0)
        # user2 follows user1
        self.assertEqual(response.data['following_count'], 1)
        # user1 doesn't follow user2
        self.assertFalse(response.data['is_following'])

    def test_get_followers(self):
        # Login as user1
        self.client.force_authenticate(user=self.user1)

        # Get user1's followers
        url = reverse('current-followers')
        response = self.client.get(url)

        # Check response
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 2)  # user2 and user3

        # Get user2's followers
        url = reverse('user-followers', kwargs={'user_id': self.user2.id})
        response = self.client.get(url)

        # Check response
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # No followers for user2
        self.assertEqual(len(response.data['results']), 0)

    def test_get_following(self):
        # Login as user1
        self.client.force_authenticate(user=self.user1)

        # Get who user1 is following
        url = reverse('current-following')
        response = self.client.get(url)

        # Check response
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)  # user3

        # Get who user2 is following
        url = reverse('user-following', kwargs={'user_id': self.user2.id})
        response = self.client.get(url)

        # Check response
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)  # user1

    def test_authentication_required(self):
        # Logout
        self.client.force_authenticate(user=None)

        # Try to follow a user
        url = reverse('follow-user', kwargs={'user_id': self.user2.id})
        response = self.client.post(url)

        # Check authentication is required
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)



class BlockAPITests(APITestCase):
    """Test the Block API endpoints"""

    def setUp(self):
        self.user1 = User.objects.create_user(
            username='user1',
            email='user1@example.com',
            password='password1'
        )
        self.user2 = User.objects.create_user(
            username='user2',
            email='user2@example.com',
            password='password2'
        )

        self.client = APIClient()

        # Create follow relationships
        Follow.follow(self.user1, self.user2)
        Follow.follow(self.user2, self.user1)

    def test_block_user(self):
        # Login as user1
        self.client.force_authenticate(user=self.user1)

        # Block user2
        url = reverse('block-user', kwargs={'user_id': self.user2.id})
        data = {'reason': 'Testing block functionality'}
        response = self.client.post(url, data)

        # Check response
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # Verify block and follow status
        self.assertTrue(Block.is_blocked(self.user1, self.user2))
        self.assertFalse(Follow.is_following(self.user1, self.user2))
        self.assertFalse(Follow.is_following(self.user2, self.user1))

    def test_unblock_user(self):
        # Login as user1
        self.client.force_authenticate(user=self.user1)

        # First block user2
        Block.block_user(self.user1, self.user2)

        # Unblock user2
        url = reverse('unblock-user', kwargs={'user_id': self.user2.id})
        response = self.client.delete(url)

        # Check response
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        # Verify block is removed
        self.assertFalse(Block.is_blocked(self.user1, self.user2))

    def test_get_blocked_users(self):
        # Login as user1
        self.client.force_authenticate(user=self.user1)

        # Block user2
        Block.block_user(self.user1, self.user2)

        # Get blocked users list
        url = reverse('blocked-users')
        response = self.client.get(url)

        # Check response
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)  # user2

    def test_follow_after_block(self):
        # Login as user1
        self.client.force_authenticate(user=self.user1)

        # Block user2
        Block.block_user(self.user1, self.user2)

        # Try to follow user2
        url = reverse('follow-user', kwargs={'user_id': self.user2.id})
        response = self.client.post(url)

        # Check follow is prevented due to block
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertFalse(Follow.is_following(self.user1, self.user2))

    def test_authentication_required_for_block(self):
        # Logout
        self.client.force_authenticate(user=None)

        # Try to block a user
        url = reverse('block-user', kwargs={'user_id': self.user2.id})
        response = self.client.post(url)

        # Check authentication is required
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)



class SocialServiceIntegrationTests(APITestCase):
    """Integration tests for the social service"""

    def setUp(self):
        self.user1 = User.objects.create_user(
            username='user1',
            email='user1@example.com',
            password='password1'
        )
        self.user2 = User.objects.create_user(
            username='user2',
            email='user2@example.com',
            password='password2'
        )

        self.client = APIClient()

    def test_follow_block_unblock_flow(self):
        # Login as user1
        self.client.force_authenticate(user=self.user1)

        # 1. Follow user2
        follow_url = reverse('follow-user', kwargs={'user_id': self.user2.id})
        response = self.client.post(follow_url)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(Follow.is_following(self.user1, self.user2))

        # 2. Check following list
        following_url = reverse('current-following')
        response = self.client.get(following_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)

        # 3. Block user2
        block_url = reverse('block-user', kwargs={'user_id': self.user2.id})
        response = self.client.post(block_url)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # 4. Verify follow relation is removed
        self.assertFalse(Follow.is_following(self.user1, self.user2))

        # 5. Check following list again
        response = self.client.get(following_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 0)

        # 6. Check blocked list
        blocked_url = reverse('blocked-users')
        response = self.client.get(blocked_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)

        # 7. Unblock user2
        unblock_url = reverse(
            'unblock-user', kwargs={'user_id': self.user2.id})
        response = self.client.delete(unblock_url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        # 8. Follow again
        response = self.client.post(follow_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(Follow.is_following(self.user1, self.user2))

        # 9. Check following list
        response = self.client.get(following_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)

    def test_multiple_user_interaction(self):
        # Create more users
        user3 = User.objects.create_user(
            username='user3',
            email='user3@example.com',
            password='password3'
        )
        user4 = User.objects.create_user(
            username='user4',
            email='user4@example.com',
            password='password4'
        )

        # Login as user1
        self.client.force_authenticate(user=self.user1)

        # 1. User1 follows user2, user3, and user4
        for user in [self.user2, user3, user4]:
            url = reverse('follow-user', kwargs={'user_id': user.id})
            self.client.post(url)

        # 2. Check user1's following count
        status_url = reverse('follow-status')
        response = self.client.get(status_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['following_count'], 3)

        # 3. Login as user2
        self.client.force_authenticate(user=self.user2)

        # 4. User2 follows user1
        url = reverse('follow-user', kwargs={'user_id': self.user1.id})
        self.client.post(url)

        # 5. User2 blocks user3
        url = reverse('block-user', kwargs={'user_id': user3.id})
        self.client.post(url)

        # 6. Check user1's followers (should include user2)
        url = reverse('user-followers', kwargs={'user_id': self.user1.id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)

        # 7. Login as user3
        self.client.force_authenticate(user=user3)

        # 8. User3 tries to follow user2 (should fail due to block)
        url = reverse('follow-user', kwargs={'user_id': self.user2.id})
        response = self.client.post(url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        # 9. User3 follows user1
        url = reverse('follow-user', kwargs={'user_id': self.user1.id})
        self.client.post(url)

        # 10. Check user1's followers (should now include user2 and user3)
        url = reverse('user-followers', kwargs={'user_id': self.user1.id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 2)



class UserDataValidationTests(APITestCase):
    """Tests to ensure user data is correctly handled"""

    def setUp(self):
        self.user1 = User.objects.create_user(
            username='testuser1',
            email='testuser1@example.com',
            password='securepassword1'
        )
        self.user2 = User.objects.create_user(
            username='testuser2',
            email='testuser2@example.com',
            password='securepassword2'
        )

        self.client = APIClient()
        self.client.force_authenticate(user=self.user1)

        # Create a follow relationship
        Follow.follow(self.user1, self.user2)

    def test_user_data_in_follow_response(self):
        """Test that user data is correctly included in follow responses"""
        # Get following list
        url = reverse('current-following')
        response = self.client.get(url)

        # Check response
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # This should return a json with pagination data
        self.assertEqual(len(response.data['results']), 1)

        # Verify user data
        user_data = response.data['results'][0]['following_details']
        self.assertEqual(user_data['username'], 'testuser2')
        # Email should not be exposed in the response for privacy
        self.assertNotIn('email', user_data)

    def test_user_data_in_followers_response(self):
        """Test that user data is correctly included in followers responses"""
        # First, make user2 follow user1
        self.client.force_authenticate(user=self.user2)
        url = reverse('follow-user', kwargs={'user_id': self.user1.id})
        self.client.post(url)

        # Now get user1's followers as user1
        self.client.force_authenticate(user=self.user1)
        url = reverse('current-followers')
        response = self.client.get(url)

        # Check response
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)

        # Verify user data
        user_data = response.data['results'][0]['follower_details']
        self.assertEqual(user_data['username'], 'testuser2')
        # Email should not be exposed in the response for privacy
        self.assertNotIn('email', user_data)

    def test_user_data_in_blocked_response(self):
        """Test that user data is correctly included in blocked users responses"""
        # Block user2
        url = reverse('block-user', kwargs={'user_id': self.user2.id})
        self.client.post(url)

        # Get blocked users
        url = reverse('blocked-users')
        response = self.client.get(url)

        # Check response
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)

        # Verify user data
        user_data = response.data['results'][0]['blocked_details']
        self.assertEqual(user_data['username'], 'testuser2')
        # Email should not be exposed in the response for privacy
        self.assertNotIn('email', user_data)
