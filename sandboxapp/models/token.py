import asyncio
from pydantic import validator
from enum import IntEnum
from datetime import datetime

from uengine.models import StorableModel, ObjectIdType
from uengine.utils import uuid4_string, now
from uengine import ctx

from sandboxapp.errors import InvalidUserId

DEFAULT_TOKEN_EXPIRATION_TIME = 87600 * 7 * 2
DEFAULT_TOKEN_AUTO_PROLONGATION = True


class TokenType(IntEnum):
    auth = 1


class Token(StorableModel):
    token: str = None
    user_id: ObjectIdType = ...
    type: TokenType = TokenType.auth
    created_at: datetime = None
    updated_at: datetime = None

    __key_field__ = "token"
    __rejected_fields__ = {"token", "user_id", "type"}
    __indexes__ = [
        ["token", {"unique": True}],
        ["user_id", "type"]
    ]

    def touch(self):
        self.updated_at = now()

    @validator('created_at', pre=True, always=True)
    def set_created_at_default(cls, value):
        return value or now()

    @validator('updated_at', pre=True, always=True)
    def set_updated_at_default(cls, value):
        return value or now()

    @validator('token', pre=True, always=True)
    def create_token_string(cls, value):
        if not value:
            value = uuid4_string()
        return value

    def user(self):
        from .user import User
        if self.user_id is None:
            return None
        loop = asyncio.get_event_loop()
        return loop.run_until_complete(User.find_one({"_id": self.user_id}))

    @property
    def expired(self):
        expiration_time = ctx.cfg.get("token_expiration_time", DEFAULT_TOKEN_EXPIRATION_TIME)
        if expiration_time <= 0:
            return False

        auto_prolongation = ctx.cfg.get("token_auto_prolongation", DEFAULT_TOKEN_AUTO_PROLONGATION)
        token_lifetime_start = self.updated_at if auto_prolongation else self.created_at
        token_lifetime = now() - token_lifetime_start

        return token_lifetime.total_seconds() > expiration_time

    def _before_save(self):
        if not self.user:
            raise InvalidUserId(self.user_id)
        if not self.is_new:
            self.touch()
