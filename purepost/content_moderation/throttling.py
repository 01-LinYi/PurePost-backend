# throttling.py
from rest_framework.throttling import UserRateThrottle

class ReportRateThrottle(UserRateThrottle):
    """Prevent users from reporting too many posts in a short time."""
    rate = '1000/hour'  # Each user can report 1000 posts per hour