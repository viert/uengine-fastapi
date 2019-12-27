from datetime import datetime
from fastapi import APIRouter, Depends

from uengine.errors import Forbidden
from uengine.api import (paginated, pagination_params, fields_param, filter_params,
                         PaginationParams, FilterParams)

from sandboxapp.auth import set_current_user
from sandboxapp.views.work_groups import WorkGroupView
from sandboxapp.models import WorkGroup

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
