from fastapi import Depends
from starlette.requests import Request

from uengine.errors import AuthenticationError
from uengine.sessions import acquire_session

from sandboxapp.models.token import Token, TokenType
from sandboxapp.models import Session


def set_current_user(required: bool = True):
    async def auth_wrapper(request: Request, session: Session = Depends(acquire_session)):
        user = None
        if "X-Api-Auth-Token" in request.headers:
            token = await Token.get(request.headers["X-Api-Auth-Token"])
            if token and token.type == TokenType.auth and not token.expired:
                user = await token.user()
        elif session:
            if session.user_id:
                user = await session.user()

        if required and not user:
            raise AuthenticationError()

        return user
    return auth_wrapper
