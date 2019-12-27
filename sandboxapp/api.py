from collections import namedtuple
from uengine.api import filter_expr

FilterParams = namedtuple("_FilterParams", field_names=["name", "mine"])


def filter_params(_filter: str = None, _mine: bool = True) -> FilterParams:
    name_filter = None
    if _filter:
        name_filter = filter_expr(_filter)
    return FilterParams(name=name_filter, mine=_mine)
