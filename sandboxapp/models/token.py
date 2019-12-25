from bson.objectid import ObjectId
from enum import IntEnum
from datetime import datetime

from uengine.models import StorableModel
from uengine.utils import uuid4_string, now
from uengine import ctx

from sandboxapp.errors import InvalidUserId

DEFAULT_TOKEN_EXPIRATION_TIME = 87600 * 7 * 2
DEFAULT_TOKEN_AUTO_PROLONGATION = True


class TokenType(IntEnum):
    auth = 1


class Token(StorableModel):
    token: str = uuid4_string
    user_id: ObjectId = ...
    type: TokenType = TokenType.auth
    created_at: datetime = now
    updated_at: datetime = now

    __key_field__ = "token"
    __rejected_fields__ = {"token", "user_id", "type"}
    __indexes__ = [
        ["token", {"unique": True}],
        ["user_id", "type"]
    ]

    def touch(self):
        self.updated_at = now()

    async def user(self):
        from .user import User
        if self.user_id is None:
            return None
        return await User.find_one({"_id": self.user_id})

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
