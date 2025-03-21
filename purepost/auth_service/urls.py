from django.urls import path
from .views import RegisterView, LoginView, LogoutView, DeleteAccountView, EmailVerificationView

urlpatterns = [
    path('register/', RegisterView.as_view(), name='register'),
    path('login/', LoginView.as_view(), name='login'),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('delete-account/', DeleteAccountView.as_view(), name='delete-account'),
    path('verify/', EmailVerificationView.as_view(), name='verify'),
]
