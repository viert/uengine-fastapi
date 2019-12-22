from fastapi import APIRouter, Depends
from uengine.api import paginated, pagination_params
from sandboxapp.models import User

users = APIRouter()


@users.get("/")
async def index(pagination: dict = Depends(pagination_params)):
    data = User.find({}).sort("username")
    data = await paginated(data, pagination["page"], pagination["limit"], pagination["nopaging"])
    return data

