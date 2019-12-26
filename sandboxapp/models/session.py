from uengine.sessions import BaseSession
from bson.objectid import ObjectId


class Session(BaseSession):
    user_id: ObjectId = None

    __indexes__ = (
        "user_id",
    )

    async def user(self):
        from .user import User
        return await User.find_one({"_id": self.user_id})
