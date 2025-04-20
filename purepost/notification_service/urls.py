from django.urls import path
from . import views

urlpatterns = [
    # Get all notifications for the current user
    path('', views.NotificationListView.as_view(), name='notification-list'),

    # Mark notifications as read
    path('mark-read/', views.MarkNotificationsReadView.as_view(), name='mark-notifications-read'),

    # Delete notifications
    path('delete/', views.DeleteNotificationsView.as_view(), name='delete-notifications'),
]