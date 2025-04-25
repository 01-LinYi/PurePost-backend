from django.urls import path
from . import views

urlpatterns = [
    # Get all notifications for the current user
    path('', views.NotificationListView.as_view(), name='notification-list'),

    # Mark notifications as read
    path('mark-read/', views.MarkNotificationsReadView.as_view(), name='mark-notifications-read'),

    # Delete notifications
    path('delete/', views.DeleteNotificationsView.as_view(), name='delete-notifications'),

    # Get all available notification types
    path('types/', views.NotificationTypesView.as_view(), name='notification-types'),

    # Get and manage notification preferences
    path('preferences/', views.NotificationPreferenceListView.as_view(), name='notification-preferences'),

    path('preferences/<str:notification_type>/', views.NotificationPreferenceDetailView.as_view(), name='notification-preference-detail'),
]