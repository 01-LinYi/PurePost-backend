from django.urls import path

from purepost.message_service import views

urlpatterns = [
    path('conv/', views.ConversationListCreateView.as_view(), name='conversation'),
    path('conv/<uuid:pk>/', views.ConversationUpdateView.as_view(), name='conversation'),
]