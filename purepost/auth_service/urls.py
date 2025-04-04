from django.urls import path
from .views import *


urlpatterns = [
    path('register/', RegisterView.as_view(), name='register'),
    path('login/', LoginView.as_view(), name='login'),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('delete-account/', DeleteAccountView.as_view(), name='delete-account'),
    path('user-visibility/', UserVisibilityView.as_view(), name='user-visibility'),
    path('followings/', FollowingsView.as_view(), name='followings'),
    path('followers/', FollowersView.as_view(), name='followers'),
    path('follow/<int:user_id>/', FollowUserView.as_view(), name='follow-user'),
    path('unfollow/<int:user_id>/', UnfollowUserView.as_view(), name='unfollow-user'),
    path('verify/', EmailVerificationView.as_view(), name='verify'),
    path('forget/', ForgetPasswordView.as_view(), name='forget-password'),
]
