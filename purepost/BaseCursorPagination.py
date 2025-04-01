from rest_framework.pagination import CursorPagination

from purepost import settings


class BaseCursorPagination(CursorPagination):
    """Base cursor pagination class"""
    page_size = settings.REST_FRAMEWORK['PAGE_SIZE']
    page_size_query_param = 'page_size'
    max_page_size = 100  # Maximum page size
    ordering = '-created_at'
