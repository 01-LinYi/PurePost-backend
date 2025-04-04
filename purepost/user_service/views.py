from typing import Any

from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, generics
from rest_framework.permissions import IsAuthenticated

from .models import Profile
from .serializers import ProfileSerializer


class ProfileDetailView(generics.RetrieveAPIView):
    """
    Retrieve the profile information of a specific user by their username.

    This view is public, meaning anyone can access it to view a user's public profile.
    """
    queryset = Profile.objects.all()
    serializer_class = ProfileSerializer
    # Specify lookup by username in the User model
    lookup_field: str = "user__username"

    def get_object(self) -> Profile:
        """
        Override the default method to retrieve a Profile object based on the 
        username provided in the URL.
        """
        username: str = self.kwargs.get(
            "username")  # Extract the username from the URL
        return get_object_or_404(Profile, user__username=username)


class MyProfileView(APIView):
    """
    Retrieve the profile of the currently logged-in user.

    This view is accessible only to authenticated users. It fetches the Profile
    associated with the currently logged-in user's account.
    """
    permission_classes: list = [IsAuthenticated]

    def get(self, request: Any, *args: Any, **kwargs: Any) -> Response:
        """
        Handle GET requests to fetch the profile of the logged-in user.
        """
        profile: Profile = get_object_or_404(Profile, user=request.user)
        serializer: ProfileSerializer = ProfileSerializer(profile, context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)


class UpdateProfileView(generics.UpdateAPIView):
    """
    Allow the currently logged-in user to update their own profile.

    This view ensures that only authenticated users can update their profile.
    """
    serializer_class = ProfileSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self) -> Profile:
        """
        Retrieve the Profile object for the currently logged-in user.
        """
        return get_object_or_404(Profile, user=self.request.user)

    def perform_update(self, serializer: ProfileSerializer) -> None:
        """
        Optionally override to add additional logic when updating the profile.

        Currently, this method simply saves the serializer, but additional
        validation or side effects can be added here if needed.
        """
        serializer.save()


class SearchProfileView(generics.ListAPIView):
    """
    Search for profiles using the input username.

    This view allows searching for profiles whose usernames partially or fully match
    the provided input. It uses a case-insensitive search.
    """
    serializer_class = ProfileSerializer
    permission_classes = [IsAuthenticated]
    queryset = Profile.objects.all()
    user_model = get_user_model()

    def get_queryset(self):
        """
        Override to filter profiles based on username query.

        The search is case-insensitive and checks for users with usernames that
        partially or fully match the provided 'username' query parameter, and then
        retrieves their associated profiles.
        """
        username_query = self.request.query_params.get('username', '')  # noqa
        return self.queryset.filter(user__in=self.user_model.objects.filter(username__icontains=username_query))
