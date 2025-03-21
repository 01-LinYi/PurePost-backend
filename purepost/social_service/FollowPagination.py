from rest_framework.pagination import CursorPagination

from purepost import settings


class FollowPagination(CursorPagination):
    page_size = settings.REST_FRAMEWORK['PAGE_SIZE']
    ordering = '-created_at'
