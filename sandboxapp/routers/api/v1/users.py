from fastapi import APIRouter, Depends
from uengine.api import paginated, pagination_params, fields_param
from sandboxapp.models import User

users = APIRouter()


@users.get("/")
async def index(pagination: dict = Depends(pagination_params), fields: list = Depends(fields_param)):
    data = User.find({}).sort("username")
    data = await paginated(data, pagination=pagination, fields=fields)
    return data


@users.get("/{user_id}")
async def show(user_id: str, fields: list = Depends(fields_param)):
    user = await User.get(user_id, "user not found")
    return {"data": user.to_dict()}
