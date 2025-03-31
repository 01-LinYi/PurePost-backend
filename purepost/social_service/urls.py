from django.urls import path

from purepost.social_service import views

urlpatterns = [
    # Follow status
    path("follow/status/", views.FollowStatusView.as_view(), name="follow-status"),
    path("follow/status/<int:user_id>/", views.FollowStatusView.as_view(), name="user-follow-status"),
    
    # Current user's relationships
    path("following/", views.CurrentFollowingListView.as_view(), name="current-following"),
    path("followers/", views.CurrentFollowerListView.as_view(), name="current-followers"),
    path("blocked/", views.BlockedUserListView.as_view(), name="blocked-users"),
    
    # Other user's relationships
    path("following/<int:user_id>/", views.UserFollowingListView.as_view(), name="user-following"),
    path("followers/<int:user_id>/", views.UserFollowerListView.as_view(), name="user-followers"),
    
    # Actions - Follow/Unfollow
    path("follow/<int:user_id>/", views.FollowCreateView.as_view(), name="follow-user"),
    path("unfollow/<int:user_id>/", views.FollowDestroyView.as_view(), name="unfollow-user"),
    
    # Actions - Block/Unblock
    path("block/<int:user_id>/", views.BlockCreateView.as_view(), name="block-user"),
    path("unblock/<int:user_id>/", views.BlockDestroyView.as_view(), name="unblock-user"),
    
    # Backward compatibility with old URLs (if needed)
    path("follower/", views.CurrentFollowerListView.as_view(), name="current-follower"),
    path("follower/<int:user_id>/", views.UserFollowerListView.as_view(), name="other-follower"),
]