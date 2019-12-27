import aiohttp
from fastapi import APIRouter, Depends
from starlette.responses import RedirectResponse

from uengine import ctx
from uengine.errors import Authenticated, AuthenticationError, ConfigurationError

from sandboxapp.auth import set_current_user, acquire_session
from sandboxapp.models import User
from sandboxapp.views.users import UserSettings
from sandboxapp.views.auth import  AuthForm


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


@account.post("/logout")
def logout(session=Depends(acquire_session)):
    session.user_id = None
    session.modified = True
    raise AuthenticationError("logged out")


@account.get("/oauth_callback")
async def oauth_callback(code: str, session=Depends(acquire_session)):
    oauth = ctx.cfg.get("oauth")
    if not oauth or "id" not in oauth or "secret" not in oauth:
        raise ConfigurationError("oauth is not configured properly")

    callback_url = oauth.get("callback_url")
    redirect_url = oauth.get("redirect_url")
    token_acquire_url = oauth.get("token_acquire_url")
    user_info_url = oauth.get("user_info_url")
    payload = {
        "client_id": oauth["id"],
        "client_secret": oauth["secret"],
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": callback_url
    }

    async with aiohttp.ClientSession() as http:
        resp = await http.post(token_acquire_url, data=payload)
        access_data = await resp.json()

        if "access_token" not in access_data:
            ctx.log.error("no token in oauth data: %s", access_data)
            raise AuthenticationError()
        else:
            token = access_data["access_token"]
            resp = await http.get(
                user_info_url,
                headers={"Authorization": f"Bearer {token}"}
            )
            user_data = await resp.json()
            user = await User.find_one({"ext_id": user_data["id"]})
            print(user_data)
            if user is None:
                user = User(
                    first_name=user_data["first_name"],
                    last_name=user_data["last_name"],
                    username=user_data["username"],
                    ext_id=user_data["id"],
                    email=user_data["email"]
                )
                await user.save()
            session.user_id = user._id
            session.modified = True
        return RedirectResponse(redirect_url, status_code=302)
