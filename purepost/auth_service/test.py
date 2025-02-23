from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase
from rest_framework import status
from rest_framework.authtoken.models import Token 

User = get_user_model()

class AuthTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="testuser", email="test@example.com", password="testpassword")
        self.token = Token.objects.create(user=self.user)
    
    def test_register(self):
        response = self.client.post('/auth/register/', {"username": "newuser", "email": "new@example.com", "password": "newpassword"})
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_login(self):
        response = self.client.post('/auth/login/', {"username": "testuser", "password": "testpassword"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_delete_account(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.token.key}')
        response = self.client.post('/auth/delete-account/', {"password": "testpassword"})
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)