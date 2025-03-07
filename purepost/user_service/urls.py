from django.urls import path

from .views import ProfileDetailView, MyProfileView, UpdateProfileView, SearchProfileView

urlpatterns = [
    # Retrieve a public user's profile by username.
    path("profiles/<str:username>/", ProfileDetailView.as_view(), name="profile-detail"),

    # Retrieve the currently logged-in user's profile.
    path("my-profile/", MyProfileView.as_view(), name="my-profile"),

    # Update the currently logged-in user's profile.
    path("update-profile/", UpdateProfileView.as_view(), name="update-profile"),

    path("search/", SearchProfileView.as_view(), name="profile-search"),
]
