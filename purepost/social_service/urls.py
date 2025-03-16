from django.urls import path

from purepost.social_service import views

urlpatterns = [
    path("following/", views.CurrentFollowingService.as_view(), name="current-following"),
    path("follower/", views.CurrentFollowerService.as_view(), name="current-follower"),
    path("following/<int:user_id>", views.OtherFollowingService.as_view(), name="other-following"),
    path("follower/<int:user_id>", views.OtherFollowerService.as_view(), name="other-follower"),
]
