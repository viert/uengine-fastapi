from math import ceil
from uengine import ctx
from uengine.db import ObjectsCursor

DEFAULT_DOCUMENTS_PER_PAGE = 20


def pagination_params(_page: int = 1, _limit: int = 0, _nopaging: bool = False):
    if not _limit:
        _limit = ctx.cfg.get("documents_per_page", DEFAULT_DOCUMENTS_PER_PAGE)
    return {"limit": _limit, "page": _page, "nopaging": _nopaging}


def fields_param(_fields: str = None):
    if _fields:
        return {"fields": _fields.split(",")}
    return {"fields": None}


async def paginated(data: ObjectsCursor, page: int, limit: int, nopaging: bool = False, extra: dict = None):
    if nopaging:
        page = None
        limit = None

    count = await data.cursor.collection.count_documents(data.query)
    if limit is not None and page is not None:
        data = data.skip((page - 1) * limit).limit(limit)

    total_pages = ceil(count / limit) if limit is not None else None

    result = {
        "page": page,
        "total_pages": total_pages,
        "count": count,
        "data": await data.all(),
    }

    if extra is not None:
        for k, v in extra.items():
            if k not in result:
                result[k] = v

    return result