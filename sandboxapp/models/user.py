from uengine.models.storable_model import StorableModel
from uengine.utils import now
from datetime import datetime
from pydantic import validator


class User(StorableModel):
    username: str
    first_name: str = ""
    last_name: str = ""
    email: str = None
    ext_id: int = None
    avatar_url: str = None
    created_at: datetime = None
    updated_at: datetime = None
    password_hash: str = "-"
    supervisor: bool = False

    __key_field__ = "username"

    __restricted_fields__ = {
        "password_hash",
    }

    __rejected_fields__ = {
        "password_hash",
        "supervisor",
        "created_at",
        "updated_at",
    }

    __indexes__ = (
        ["username", {"unique": True}],
        "ext_id",
    )

    @validator('created_at', pre=True, always=True)
    def set_created_at_default(cls, value):
        return value or now()

    @validator('updated_at', pre=True, always=True)
    def set_updated_at_default(cls, value):
        return value or now()

    async def get_auth_token(self):
        from .token import Token, TokenType
        tokens = Token.find({"type": TokenType.auth, "user_id": self._id})
        async for token in tokens:
            if not token.expired:
                return token
        token = Token(type=TokenType.auth, user_id=self._id)
        await token.save()
        return token
