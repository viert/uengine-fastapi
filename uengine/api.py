import re
import asyncio
from collections import namedtuple
from typing import Callable, Iterable
from math import ceil

from uengine import ctx
from uengine.db import ObjectsCursor
from uengine.models.abstract_model import AbstractModel


DEFAULT_DOCUMENTS_PER_PAGE = 20

PaginationParams = namedtuple("_PaginationParams", field_names=["limit", "page", "nopaging"])


def filter_expr(flt):
    if flt.find(" ") >= 0:
        tokens = flt.split()
        return {"$in": tokens}
    try:
        return re.compile(flt, re.IGNORECASE)
    # re.compile's can throw multiple different exceptions,
    # we do not care about what exactly went wrong
    except Exception:
        return ""


def pagination_params(_page: int = 1, _limit: int = 0, _nopaging: bool = False) -> PaginationParams:
    if not _limit:
        _limit = ctx.cfg.get("documents_per_page", DEFAULT_DOCUMENTS_PER_PAGE)
    return PaginationParams(limit=_limit, page=_page, nopaging=_nopaging)


def fields_param(_fields: str = None):
    if _fields:
        return _fields.split(",")
    return None


async def default_transform(item: AbstractModel, fields: Iterable = None) -> dict:
    return await item.to_dict(fields=fields)


async def paginated(data: ObjectsCursor,
                    pagination: PaginationParams,
                    extra: dict = None,
                    fields: Iterable = None,
                    transform: Callable[[AbstractModel, Iterable], dict] = default_transform):
    page, limit, nopaging = pagination.page, pagination.limit, pagination.nopaging
    if nopaging:
        page = None
        limit = None

    count = await data.cursor.collection.count_documents(data.query)
    if limit is not None and page is not None:
        data = data.skip((page - 1) * limit).limit(limit)

    total_pages = ceil(count / limit) if limit is not None else None

    data_tasks = [asyncio.create_task(transform(item, fields)) for item in await data.all()]
    data = await asyncio.gather(*data_tasks)

    result = {
        "page": page,
        "total_pages": total_pages,
        "count": count,
        "data": data,
    }

    if extra is not None:
        for k, v in extra.items():
            if k not in result:
                result[k] = v

    return result
