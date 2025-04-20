# throttling.py
from rest_framework.throttling import UserRateThrottle

class ReportRateThrottle(UserRateThrottle):
    """Prevent users from reporting too many posts in a short time."""
    rate = '10/hour'  # Each user can report 10 posts per hour