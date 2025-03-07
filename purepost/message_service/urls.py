from django.urls import path

from purepost.message_service import views

urlpatterns = [
    path('conv/', views.ConversationOverviewView.as_view(), name='conversation'),
    path('conv/<uuid:pk>/', views.ConversationDetailView.as_view(), name='conversation'),
]