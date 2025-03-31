from rest_framework.pagination import CursorPagination

from purepost import settings


class BaseCursorPagination(CursorPagination):
    """Base cursor pagination class"""
    page_size = settings.REST_FRAMEWORK['PAGE_SIZE']
    page_size_query_param = 'page_size'
    max_page_size = 100  # Maximum page size


class FollowPagination(BaseCursorPagination):
    """Follow relationship's  pagination"""
    ordering = '-created_at'


class BlockPagination(BaseCursorPagination):
    """Blocks pagination"""
    ordering = '-created_at'


class FollowerPagination(BaseCursorPagination):
    """Followers pagination"""
    ordering = '-created_at'
    

class FollowingPagination(BaseCursorPagination):
    """Following pagination"""
    ordering = '-created_at'