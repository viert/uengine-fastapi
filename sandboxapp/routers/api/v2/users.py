from fastapi import APIRouter, Depends
from uengine.api import paginated, pagination_params, fields_param, PaginationParams
from sandboxapp.models import User
from sandboxapp.auth import set_current_user

users = APIRouter()


@users.get("/", dependencies=[Depends(set_current_user(required=False))])
async def index(
        pagination: PaginationParams = Depends(pagination_params),
        fields: list = Depends(fields_param)):
    data = User.find({}).sort("username")
    data = await paginated(data, pagination=pagination, fields=fields)
    return data


@users.get("/{user_id}", dependencies=[Depends(set_current_user(required=False))])
async def show(user_id: str,
               fields: list = Depends(fields_param)):
    user = await User.get(user_id, "user not found")
    return {"data": await user.to_dict(fields=fields)}
