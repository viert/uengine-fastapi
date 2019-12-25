from fastapi import APIRouter, Depends
from sandboxapp.auth import set_current_user

account = APIRouter()


@account.get("/me")
async def me(user=Depends(set_current_user(True))):
    data = user.to_dict()
    token = await user.get_auth_token()
    data["auth_token"] = token.token
    return {"data": data}
