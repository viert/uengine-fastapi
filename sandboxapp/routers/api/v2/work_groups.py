import asyncio
from datetime import datetime
from fastapi import APIRouter, Depends

from uengine.errors import Forbidden, InputDataError
from uengine.api import (paginated, pagination_params, fields_param, filter_params,
                         PaginationParams, FilterParams)

from sandboxapp.auth import set_current_user
from sandboxapp.views.work_groups import WorkGroupView, Owner, Members
from sandboxapp.models import WorkGroup, User

work_groups = APIRouter()


@work_groups.get("/")
async def index(
        _since: datetime = None,
        filters: FilterParams = Depends(filter_params),
        user=Depends(set_current_user()),
        pagination: PaginationParams = Depends(pagination_params),
        fields: list = Depends(fields_param)):

    query = {}
    if filters.name:
        query["name"] = filters.name

    if filters.mine:
        query["$or"] = [
            {"owner_id": user._id},
            {"member_ids": user._id},
        ]

    if _since:
        query["updated_at"] = {"$gte": _since}

    data = WorkGroup.find(query).sort("name", 1)
    data = await paginated(data, pagination=pagination, fields=fields)
    return data


@work_groups.get("/{work_group_id}")
async def show(work_group_id: str,
               user=Depends(set_current_user()),
               fields: list = Depends(fields_param)):
    wg = await WorkGroup.get(work_group_id, "work_group not found")
    data = await wg.to_dict(fields=fields)

    if fields and "modification_allowed" in fields:
        data["modification_allowed"] = wg.modification_allowed(user)

    return {"data": data}


@work_groups.post("/")
async def create(data: WorkGroupView,
                 fields: list = Depends(fields_param),
                 user=Depends(set_current_user())):
    data = data.dict()
    data["owner_id"] = user._id
    wg = WorkGroup(**data)
    await wg.save()

    data = await wg.to_dict(fields=fields)
    if fields and "modification_allowed" in fields:
        data["modification_allowed"] = wg.modification_allowed(user)

    return {
        "data": data,
        "message": f"workgroup {wg.name} successfully created"
    }


@work_groups.patch("/{work_group_id}")
async def update(work_group_id: str,
                 data: WorkGroupView,
                 user=Depends(set_current_user()),
                 fields: list = Depends(fields_param)):
    wg = await WorkGroup.get(work_group_id, "work_group not found")
    if not wg.modification_allowed(user):
        raise Forbidden("you don't have permission to modify this work_group")

    await wg.update(data.dict())

    data = await wg.to_dict(fields=fields)
    if fields and "modification_allowed" in fields:
        data["modification_allowed"] = wg.modification_allowed(user)

    return {
        "data": data,
        "message": f"workgroup {wg.name} successfully updated"
    }


@work_groups.delete("/{work_group_id}")
async def destroy(work_group_id: str,
                  user=Depends(set_current_user()),
                  fields: list = Depends(fields_param)):
    wg = await WorkGroup.get(work_group_id, "work_group not found")
    if not wg.member_list_modification_allowed(user):
        raise Forbidden("you don't have permission to delete this work_group")

    await wg.destroy()

    data = await wg.to_dict(fields=fields)
    if fields and "modification_allowed" in fields:
        data["modification_allowed"] = wg.modification_allowed(user)

    return {
        "data": data,
        "message": f"workgroup {wg.name} successfully deleted"
    }


@work_groups.post("/{work_group_id}/switch_owner")
async def switch_owner(work_group_id: str,
                 data: Owner,
                 user=Depends(set_current_user()),
                 fields: list = Depends(fields_param)):
    wg = await WorkGroup.get(work_group_id, "work_group not found")
    if not wg.member_list_modification_allowed(user):
        raise Forbidden("you don't have permission to change this work_group's owner")

    user = await User.get(data.owner_id, "new owner not found")
    if user._id == wg.owner_id:
        raise InputDataError("old and new owners match")

    wg.owner_id = user._id
    await wg.save()

    data = await wg.to_dict(fields=fields)
    if fields and "modification_allowed" in fields:
        data["modification_allowed"] = wg.modification_allowed(user)

    return {
        "data": data,
        "message": f"workgroup {wg.name} owner switched to {user.username}"
    }


@work_groups.post("/{work_group_id}/set_members")
async def switch_owner(work_group_id: str,
                 data: Members,
                 user=Depends(set_current_user()),
                 fields: list = Depends(fields_param)):
    wg = await WorkGroup.get(work_group_id, "work_group not found")
    if not wg.member_list_modification_allowed(user):
        raise Forbidden("you don't have permission to change this work_group's member list")

    members_gather_tasks = [asyncio.create_task(User.get(uid, f"member with id {uid} not found")) for uid in data.member_ids]
    member_ids = [m._id for m in await asyncio.gather(*members_gather_tasks)]

    if wg.owner_id in member_ids:
        member_ids.remove(wg.owner_id)

    wg.member_ids = member_ids
    await wg.save()

    data = await wg.to_dict(fields=fields)
    if fields and "modification_allowed" in fields:
        data["modification_allowed"] = wg.modification_allowed(user)

    return {
        "data": data,
        "message": f"workgroup {wg.name} members successfully set"
    }
