from fastapi import APIRouter
from sandboxapp.models import User

users = APIRouter()


@users.get("/")
async def index():
    data = await User.find({}).sort("username").all()
    return {"data": data}
