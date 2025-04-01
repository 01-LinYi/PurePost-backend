from rest_framework.pagination import CursorPagination

from purepost import settings
from purepost.BaseCursorPagination import BaseCursorPagination


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
