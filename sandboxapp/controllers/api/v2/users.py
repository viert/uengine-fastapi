from fastapi import APIRouter, Depends

from uengine.api import paginated, pagination_params, fields_param, PaginationParams
from uengine.errors import Forbidden, IntegrityError

from sandboxapp.models import User
from sandboxapp.views.users import UserView, PasswordFormData, SupervisorFormData, SystemFormData
from sandboxapp.auth import set_current_user

users = APIRouter()


@users.get("/", dependencies=[Depends(set_current_user(required=True))])
async def index(
        pagination: PaginationParams = Depends(pagination_params),
        fields: list = Depends(fields_param)):
    data = User.find({}).sort("username")
    data = await paginated(data, pagination=pagination, fields=fields)
    return data


@users.get("/{user_id}")
async def show(user_id: str,
               current=Depends(set_current_user()),
               fields: list = Depends(fields_param)):
    user = await User.get(user_id, "user not found")
    data = await user.to_dict(fields=fields)
    if fields and "modification_allowed" in fields:
        data["modification_allowed"] = user.modification_allowed(current)
    return {"data": data}


@users.post("/")
async def create(data: UserView,
                 current=Depends(set_current_user()),
                 fields: list = Depends(fields_param)):
    if not current.supervisor:
        raise Forbidden("you don't have permission to create new users")

    existing = await User.get(data.username)
    if existing is not None:
        raise IntegrityError("user exists")

    user = User(**data.dict())
    await user.save()

    data = await user.to_dict(fields=fields)
    if fields and "modification_allowed" in fields:
        data["modification_allowed"] = user.modification_allowed(current)
    return {
        "data": data,
        "message": f"user {user.username} created successfully",
    }


@users.patch("/{user_id}")
async def update(user_id: str,
                 data: UserView,
                 current=Depends(set_current_user()),
                 fields: list = Depends(fields_param)):
    user = await User.get(user_id, "user not found")
    if not user.modification_allowed(current):
        raise Forbidden("you don't have permission to modify this user")
    await user.update(data.dict())

    data = await user.to_dict(fields=fields)
    if fields and "modification_allowed" in fields:
        data["modification_allowed"] = user.modification_allowed(current)

    return {
        "data": data,
        "message": f"user {user.username} updated successfully",
    }


@users.delete("/{user_id}")
async def destroy(user_id: str,
                  current=Depends(set_current_user()),
                  fields: list = Depends(fields_param)):
    user = await User.get(user_id, "user not found")
    if not user.supervisor:
        raise Forbidden("you don't have permission to delete users")
    await user.destroy()

    data = await user.to_dict(fields=fields)
    if fields and "modification_allowed" in fields:
        data["modification_allowed"] = user.modification_allowed(current)

    return {
        "data": data,
        "message": f"user {user.username} deleted successfully",
    }


@users.post("/{user_id}/set_password")
async def set_password(user_id: str,
                       data: PasswordFormData,
                       current=Depends(set_current_user()),
                       fields: list = Depends(fields_param)):
    user = await User.get(user_id, "user not found")
    if not user.modification_allowed(current):
        raise Forbidden("you don't have permission to modify this user")
    user.set_password(data.password_raw)
    await user.save()

    data = await user.to_dict(fields=fields)
    if fields and "modification_allowed" in fields:
        data["modification_allowed"] = user.modification_allowed(current)

    return {
        "data": data,
        "message": f"user {user.username} password set",
    }


@users.post("/{user_id}/set_supervisor")
async def set_supervisor(user_id: str,
                         data: SupervisorFormData,
                         current=Depends(set_current_user()),
                         fields: list = Depends(fields_param)):

    user = await User.get(user_id, "user not found")
    if not user.supervisor_set_allowed(current):
        raise Forbidden("you don't have permission to set supervisor property for this user")

    user.supervisor = data.supervisor
    await user.save()

    data = await user.to_dict(fields=fields)
    if fields and "modification_allowed" in fields:
        data["modification_allowed"] = user.modification_allowed(current)

    action = "granted" if user.supervisor else "revoked"
    return {
        "data": data,
        "message": f"user {user.username} supervisor {action}",
    }


@users.post("/{user_id}/set_system")
async def set_system(user_id: str,
                     data: SystemFormData,
                     current=Depends(set_current_user()),
                     fields: list = Depends(fields_param)):

    user = await User.get(user_id, "user not found")
    if not user.system_set_allowed(current):
        raise Forbidden("you don't have permission to set system flag for this user")

    user.system = data.system
    await user.save()

    data = await user.to_dict(fields=fields)
    if fields and "modification_allowed" in fields:
        data["modification_allowed"] = user.modification_allowed(current)

    action = "granted" if user.system else "revoked"
    return {
        "data": data,
        "message": f"user {user.username} system flag {action}",
    }


@users.delete("/{user_id}/revoke_tokens")
async def revoke_tokens(user_id: str,
                  current=Depends(set_current_user()),
                  fields: list = Depends(fields_param)):
    user = await User.get(user_id, "user not found")
    if not user.tokens_drop_allowed(current):
        raise Forbidden("you don't have permissions to drop this user's tokens")

    await user.reset_auth_token()

    data = await user.to_dict(fields=fields)
    if fields and "modification_allowed" in fields:
        data["modification_allowed"] = user.modification_allowed(current)

    return {
        "data": data,
        "message": f"user {user.username} tokens revoked",
    }
