import bcrypt
from datetime import datetime
from typing import Union

from uengine.models.storable_model import StorableModel
from uengine.utils import now
from uengine import ctx

from sandboxapp.errors import InvalidPassword, OutOfBounds, UserHasReferences

DEFAULT_GRAVATAR_BASE_URL = "https://sys.mail.ru/avatar/internal"


def _cfgget_docs_per_page():
    return ctx.cfg.get("docs_per_page", 20)


class User(StorableModel):

    __collection__ = "users"

    ext_id: int = None
    username: str
    first_name: str = ""
    last_name: str = ""
    email: str = None
    avatar_url: str = None
    password_hash: str = "-"
    supervisor: bool = False
    system: bool = False
    created_at: datetime = now
    updated_at: datetime = now
    docs_per_page: int = _cfgget_docs_per_page
    mine_filter: bool = True

    __key_field__ = "username"

    __restricted_fields__ = {
        "password_hash",
    }

    __rejected_fields__ = {
        "password_hash",
        "supervisor",
        "system",
        "created_at",
        "updated_at",
        "ext_id",
    }

    __indexes__ = (
        ["username", {"unique": True}],
        "ext_id",
        "updated_at",
        "supervisor",
        "system",
    )

    __auto_trim_fields__ = {
        "username",
        "first_name",
        "last_name",
        "email",
    }

    def __init__(self, **kwargs):
        password_raw = None
        if "password_raw" in kwargs:
            password_raw = kwargs["password_raw"]
            del kwargs["password_raw"]
        super().__init__(**kwargs)
        if password_raw is not None:
            self.set_password(password_raw)

    async def get_auth_token(self):
        from .token import Token, TokenType
        tokens = Token.find({"type": TokenType.auth, "user_id": self._id})
        async for token in tokens:
            if token.expired:
                await token.destroy()
            else:
                return token
        token = Token(type=TokenType.auth, user_id=self._id)
        await token.save()
        return token

    async def reset_auth_token(self):
        from .token import Token
        await Token.destroy_many({"type": "auth", "user_id": self._id})

    def set_password(self, password_raw):
        if not password_raw:
            raise InvalidPassword("password can't be empty")
        self.password_hash = bcrypt.hashpw(password_raw.encode(), bcrypt.gensalt()).decode('utf-8')

    def check_password(self, password_raw):
        if self.password_hash == "-":
            return False
        return bcrypt.checkpw(password_raw.encode('utf-8'), self.password_hash.encode('utf-8'))

    async def get_all_auth_tokens(self):
        from .token import Token
        return await Token.find({"type": "auth", "user_id": self._id}).all()

    @property
    def avatar(self):
        if self.avatar_url:
            return self.avatar_url
        if not self.email:
            return ""

        from hashlib import md5
        gravatar_base = ctx.cfg.get("gravatar_base_url", DEFAULT_GRAVATAR_BASE_URL)
        gravatar_ext = ctx.cfg.get("gravatar_extension", "jpg")
        if not gravatar_base:
            return ""
        gravatar_hash = md5(self.email.strip().encode()).hexdigest()
        return f"{gravatar_base}/{gravatar_hash}.{gravatar_ext}"

    def touch(self):
        self.updated_at = now()

    @property
    def work_groups_owned(self):
        from .work_group import WorkGroup
        return WorkGroup.find({"owner_id": self._id})

    @property
    def work_groups_included_into(self):
        from .work_group import WorkGroup
        return WorkGroup.find({"member_ids": self._id})

    async def _before_save(self):
        if self.docs_per_page < 1:
            raise OutOfBounds("docs_per_page can not be less than 1")
        if not self.is_new:
            self.touch()
            self.invalidate()

    async def _before_delete(self):
        self.invalidate()
        work_groups_count = await self.work_groups_owned.count()
        if work_groups_count > 0:
            raise UserHasReferences("can't remove user with work_groups owned by")
        async for work_group in self.work_groups_included_into:
            await work_group.remove_member(self)

    @property
    def public_namespace_key(self):
        return "@" + self.username.replace(".", "_")

    @property
    def protected_namespace_key(self):
        return self.public_namespace_key + ":protected"

    def modification_allowed(self, user):
        return user._id == self._id or user.supervisor

    def supervisor_set_allowed(self, user):
        # disallow user to revoke his own supervisor status
        return user.supervisor and user._id != self._id

    def system_set_allowed(self, user):
        # disallow user to set himself system
        return user.supervisor and user._id != self._id

    def tokens_drop_allowed(self, user):
        return user._id == self._id or user.supervisor
