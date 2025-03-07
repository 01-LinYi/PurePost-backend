from urllib.parse import parse_qs
from django.contrib.auth.models import AnonymousUser
from rest_framework.authtoken.models import Token
from channels.middleware import BaseMiddleware
from asgiref.sync import sync_to_async

@sync_to_async
def get_user_from_token(token_key):
    """Fetch the user corresponding to the token."""
    try:
        token = Token.objects.get(key=token_key)
        return token.user
    except Token.DoesNotExist:
        return AnonymousUser()


class TokenAuthMiddleware(BaseMiddleware):
    """Custom token authentication middleware for Django Channels."""

    async def __call__(self, scope, receive, send):
        # Extract token from headers or query parameters
        headers = dict(scope["headers"])
        query_params = parse_qs(scope["query_string"].decode("utf-8"))
        token_key = None

        # Get the token from the query string first
        if "token" in query_params:
            token_key = query_params["token"][0]
            print(f"TokenAuthMiddleware: Token found in query params: {token_key}")

        # Validate the token
        user = await get_user_from_token(token_key) if token_key else AnonymousUser()

        # Log the result for debugging
        if isinstance(user, AnonymousUser):
            print(f"TokenAuthMiddleware: Authentication failed for token: {token_key}")
        else:
            print(f"TokenAuthMiddleware: Authenticated user: {user.username}")

        # Add the user to the scope
        scope["user"] = user

        # Proceed with the connection
        return await super().__call__(scope, receive, send)
