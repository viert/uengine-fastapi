from fastapi import APIRouter, Depends
from uengine.api import paginated, pagination_params, fields_param
from sandboxapp.models import User

users = APIRouter()


@users.get("/")
async def index(pagination: dict = Depends(pagination_params), fields: list = Depends(fields_param)):
    data = User.find({}).sort("username")
    data = await paginated(data, pagination["page"], pagination["limit"], pagination["nopaging"], fields=fields)
    return data

