from uengine.models.storable_model import StorableModel
from uengine.utils import now
from datetime import datetime


class User(StorableModel):

    username: str
    first_name: str = ""
    last_name: str = ""
    email: str = None
    ext_id: int = None
    avatar_url: str = None
    created_at: datetime = now
    updated_at: datetime = now
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

    async def get_auth_token(self):
        from .token import Token, TokenType
        tokens = Token.find({"type": TokenType.auth, "user_id": self._id})
        async for token in tokens:
            if not token.expired:
                return token
        token = Token(type=TokenType.auth, user_id=self._id)
        await token.save()
        return token
