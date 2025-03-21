import random
from datetime import timedelta

import redis
from django.contrib.auth import get_user_model, logout
from rest_framework import status, permissions
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.authtoken.models import Token
from .serializers import RegisterSerializer, LoginSerializer, DeleteAccountSerializer
from .. import settings
from ..notification_service.email_service import send_email

User = get_user_model()

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


class EmailVerificationView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @staticmethod
    def post(request):
        user = request.user

        # Generate a random 6-digit code
        verification_code = random.randint(100000, 999999)

        # Set Redis key for the verification code with a 10-minute TTL
        minute_ttl = 10
        redis_key = f"email_verification:{user.id}"
        redis_ttl = timedelta(minutes=minute_ttl)
        redis_client.setex(redis_key, redis_ttl, verification_code)

        # Send the verification code via email
        send_email(
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
    def get(request):
        user = request.user

        # Get the code from query params
        verification_code = request.query_params.get("code")

        # Retrieve the verification code from Redis
        redis_key = f"email_verification:{user.id}"
        stored_code = redis_client.get(redis_key)

        # Validate stored_code against verification_code
        if stored_code is None or stored_code != verification_code:
            return Response(
                {"error": "Verification code is invalid or expired"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Remove the code from Redis after successful verification
        redis_client.delete(redis_key)
        return Response(
            {"message": "Verification successful"},
            status=status.HTTP_200_OK
        )
