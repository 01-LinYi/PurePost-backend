import random
from datetime import timedelta

import redis
from django.contrib.auth import logout
from rest_framework import status, permissions
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.authtoken.models import Token
from .serializers import RegisterSerializer, LoginSerializer, DeleteAccountSerializer, UserSerializer

from .models import User
from .. import settings
from ..notification_service.utils import send_email_async

# Initialize Redis connection
redis_client = redis.StrictRedis(
    host=settings.REDIS_HOST,
    port=settings.REDIS_PORT,
    db=0,
    decode_responses=True  # Automatically decode Redis query results to strings
)


class RegisterView(APIView):
    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(
                {"message": "Account created successfully"},
                status=status.HTTP_201_CREATED
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class LoginView(APIView):
    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.validated_data
            token, _ = Token.objects.get_or_create(user=user)
            return Response(
                {
                    "token": token.key,
                    "user": {
                        "id": user.id,
                        "username": user.username,
                        "email": user.email,
                        "is_verified": user.is_verified,
                        "is_private": user.is_private,
                        "is_admin": user.is_admin,
                    },
                },
                status=status.HTTP_200_OK
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class LogoutView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        Token.objects.filter(user=request.user).delete()
        return Response(
            {"message": "Logout successfully"},
            status=status.HTTP_200_OK
        )


class DeleteAccountView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = DeleteAccountSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            user = request.user
            user.delete()
            logout(request)
            return Response(
                {"message": "Account deleted successfully"},
                status=status.HTTP_204_NO_CONTENT
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


'''
class FollowingsView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        """Retrieve users the authenticated user is following."""
        followings = request.user.followings.all()
        serializer = UserSerializer(followings, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class FollowersView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        """Retrieve users who are following the authenticated user."""
        followers = request.user.followers.all()
        serializer = UserSerializer(followers, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class FollowUserView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, user_id):
        """Follow a user."""
        try:
            user_to_follow = User.objects.get(id=user_id)
            request.user.follow(user_to_follow)
            return Response({"message": "Followed successfully"}, status=status.HTTP_200_OK)
        except User.DoesNotExist:
            return Response({"error": "User not found"}, status=status.HTTP_404_NOT_FOUND)


class UnfollowUserView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, user_id):
        """Unfollow a user."""
        try:
            user_to_unfollow = User.objects.get(id=user_id)
            request.user.unfollow(user_to_unfollow)
            return Response({"message": "Unfollowed successfully"}, status=status.HTTP_200_OK)
        except User.DoesNotExist:
            return Response({"error": "User not found"}, status=status.HTTP_404_NOT_FOUND)
'''


class UserVisibilityView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    # noinspection PyMethodMayBeStatic
    def update(self, request):
        """Update user visibility."""

        # Convert string to boolean
        is_private = request.data.get('isPrivate')
        if is_private is None:
            return Response({"error": "isPrivate is required"}, status=status.HTTP_400_BAD_REQUEST)

        request.user.is_private = is_private
        request.user.save()
        return Response({"message": "Visibility updated"}, status=status.HTTP_200_OK)

    def put(self, request):
        return self.update(request)

    def patch(self, request):
        return self.update(request)


class EmailVerificationView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @staticmethod
    def get(request):
        user = request.user
        if user.is_verified:
            return Response(
                {"error": "User is already verified"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Generate a random 6-digit code
        verification_code = random.randint(100000, 999999)

        # Set Redis key for the verification code with a 10-minute TTL
        minute_ttl = 10
        redis_key = f"email_verification:{user.id}"
        redis_ttl = timedelta(minutes=minute_ttl)
        redis_client.setex(redis_key, redis_ttl, verification_code)

        # Send the verification code via email
        send_email_async(
            subject="Your Verification Code",
            to_email=[user.email],
            template_name="emails/verify_email.html",
            context={
                "username": user.username,
                "verification_code": verification_code,
                "ttl": f'{minute_ttl} minutes',
            },
        )

        return Response(
            {"message": "Verification email sent successfully"},
            status=status.HTTP_200_OK
        )

    @staticmethod
    def post(request):
        user = request.user
        if user.is_verified:
            return Response(
                {"error": "User is already verified"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Get the code from query params
        verification_code = request.data.get("code")

        # Retrieve the verification code from Redis
        redis_key = f"email_verification:{user.id}"
        stored_code = redis_client.get(redis_key)

        # Validate stored_code against verification_code
        if stored_code is None or stored_code != verification_code:
            return Response(
                {"error": "Verification code is invalid or expired"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Marked user as verified
        user.is_verified = True
        user.save()

        # Remove the code from Redis after successful verification
        redis_client.delete(redis_key)
        return Response(
            {"message": "Verification successful"},
            status=status.HTTP_200_OK
        )


class ForgetPasswordView(APIView):
    @staticmethod
    def post(request):
        # Find user with the given email
        user_email = request.query_params.get("email")
        user = User.objects.filter(email=user_email).first()
        if not user:
            return Response(
                {"error": "User with the provided email does not exist."},
                status=status.HTTP_404_NOT_FOUND
            )

        # Generate a random 16-character string as the verification code
        verification_code = ''.join(
            random.choices(
                'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789',
                k=16
            )
        )

        # Set Redis key for the verification code with a 5-minute TTL
        minute_ttl = 5
        redis_key = f"forget_password_verification:{user_email}"
        redis_ttl = timedelta(minutes=minute_ttl)
        redis_client.setex(redis_key, redis_ttl, verification_code)

        # Send the verification code via email
        send_email_async(
            subject="Password Reset Verification Code",
            to_email=[user_email],
            template_name="emails/forget_password.html",
            context={
                "username": user.username,
                "verification_code": verification_code,
                "ttl": f"{minute_ttl} minutes",
            },
        )

        return Response(
            {"message": "Verification email sent successfully"},
            status=status.HTTP_200_OK
        )

    @staticmethod
    def put(request):
        # Retrieve the code, email, and new password from the request body
        verification_code = request.data.get("code")
        new_password = request.data.get("new_password")
        user_email = request.data.get("email")

        if not verification_code or not new_password or not user_email:
            return Response(
                {"error": "Email, Code, and new password are required."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Validate the new password using RegisterSerializer
        password_validation_data = {"password": new_password}
        password_serializer = RegisterSerializer(data=password_validation_data, partial=True)
        if not password_serializer.is_valid():
            return Response(
                password_serializer.errors,
                status=status.HTTP_400_BAD_REQUEST
            )

        # Get the Redis key based on the user's email
        redis_key = f"forget_password_verification:{user_email}"

        # Check if the code exists in Redis
        stored_code = redis_client.get(redis_key)
        if stored_code is None or stored_code != verification_code:
            return Response(
                {"error": "Invalid or expired verification code."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Update the user's password
        user = User.objects.filter(email=user_email).first()
        if not user:
            return Response(
                {"error": "User with the provided email does not exist."},
                status=status.HTTP_404_NOT_FOUND
            )

        user.set_password(new_password)
        user.save()

        # Delete the verification code from Redis
        redis_client.delete(redis_key)

        return Response(
            {"message": "Password updated successfully."},
            status=status.HTTP_200_OK
        )


class CheckAdminView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        return Response({
            'is_admin': request.user.is_admin,
            'is_superuser': request.user.is_superuser
        })
