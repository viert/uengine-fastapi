from fastapi import APIRouter, Depends

from uengine.errors import Authenticated, AuthenticationError
from sandboxapp.auth import set_current_user, acquire_session
from sandboxapp.models import User
from sandboxapp.views.users import UserSettings, AuthForm


account = APIRouter()

ACCOUNT_USER_FIELDS = (
    "_id",
    "ext_id",
    "username",
    "first_name",
    "last_name",
    "email",
    "avatar",
    "supervisor",
    "system",
    "auth_token",
    "mine_filter",
    "docs_per_page"
)


@account.get("/me")
async def me(user=Depends(set_current_user(required=True))):
    data = await user.to_dict(fields=ACCOUNT_USER_FIELDS)
    token = await user.get_auth_token()
    data["auth_token"] = token.token
    return {"data": data}


@account.patch("/me")
async def update_settings(settings: UserSettings, user=Depends(set_current_user(required=True))):
    data = settings.dict(exclude_none=True)
    await user.update(**data)
    data = await user.to_dict(fields=ACCOUNT_USER_FIELDS)
    token = await user.get_auth_token()
    data["auth_token"] = token.token
    return {"data": data}


@account.post("/authenticate")
async def authenticate(
        form: AuthForm,
        user=Depends(set_current_user(required=False)),
        session=Depends(acquire_session)):
    if user:
        raise Authenticated()

    user = await User.get(form.username)
    if not user:
        raise AuthenticationError("invalid credentials")

    if not user.check_password(form.password):
        raise AuthenticationError("invalid credentials")

    session.user_id = user._id
    session.modified = True

    data = await user.to_dict(fields=ACCOUNT_USER_FIELDS)
    token = await user.get_auth_token()
    data["auth_token"] = token.token
    return {"data": data}
