from bson import ObjectId
from datetime import datetime

from uengine.models.storable_model import StorableModel
from uengine.utils import now


class WorkGroup(StorableModel):

    __collection__ = "work_groups"

    name: str
    description: str = None
    email: str = None
    owner_id: ObjectId
    member_ids: list = []
    created_at: datetime = now
    updated_at: datetime = now

    __key_field__ = "name"

    __required_fields__ = {
        "member_ids",
    }

    __rejected_fields__ = {
        "created_at",
        "updated_at",
        "owner_id",
        "member_ids",
    }

    __indexes__ = (
        ["name", {"unique": True}],
        "member_ids",
        "owner_id",
        "updated_at",
    )

    __auto_trim_fields__ = {
        "name",
    }

    @property
    async def owner(self):
        from .user import User
        return await User.get(self.owner_id)

    @property
    async def owner_username(self):
        owner = await self.owner
        return owner.username

    @property
    def members(self):
        from .user import User
        return User.find({"_id": {"$in": self.member_ids}})

    @property
    async def member_usernames(self):
        return [u.username async for u in self.members]

    @property
    def participants(self):
        from .user import User
        return User.find({"_id": {"$in": self.member_ids + [self.owner_id]}})

    @property
    async def participant_usernames(self):
        return [u.username async for u in self.participants]

    def modification_allowed(self, user):
        return user.supervisor or self.owner_id == user._id

