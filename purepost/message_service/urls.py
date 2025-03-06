from django.urls import path

from purepost.message_service import views

urlpatterns = [
    path('conv/', views.ConversationView.as_view(), name='conversation'),
]