import functools
from typing import Callable
from uengine.errors import AuthenticationError
from sandboxapp.models.token import Token, TokenType
from starlette.requests import Request


def set_current_user(required: bool = True):
    async def auth_wrapper(request: Request):
        request.state.user = None

        if "X-Api-Auth-Token" in request.headers:
            token = await Token.get(request.headers["X-Api-Auth-Token"])
            if token and token.type == TokenType.auth and not token.expired:
                user = await token.user()
                request.state.user = user

        if required and not request.state.user:
            raise AuthenticationError()

        return request.state.user
    return auth_wrapper
