from rest_framework import viewsets, permissions
from .models import Feedback
from .serializers import FeedbackSerializer
from purepost.auth_service.permissions import IsAdminUser

class FeedbackViewSet(viewsets.ModelViewSet):
    serializer_class = FeedbackSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Feedback.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

class FeedbackAdminViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Admin-only ViewSet for listing and retrieving all feedback submissions.
    """
    queryset = Feedback.objects.all()
    serializer_class = FeedbackSerializer
    permission_classes = [IsAdminUser]

    def get_queryset(self):
        queryset = Feedback.objects.all()
        feedback_type = self.request.query_params.get('type')
        is_finished = self.request.query_params.get('finished')

        if feedback_type:
            queryset = queryset.filter(feedback_type=feedback_type)
        if is_finished in ['true', 'false']:
            queryset = queryset.filter(is_finished=(is_finished == 'true'))

        return queryset