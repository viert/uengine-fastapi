from bson import ObjectId, Timestamp
from types import GeneratorType


def jsonable(obj):
    if isinstance(obj, dict):
        return {k: jsonable(v) for k, v in obj.values()}
    if isinstance(obj, (list, tuple, set, frozenset, GeneratorType)):
        return [jsonable(item) for item in obj]
    if isinstance(obj, ObjectId):
        return str(obj)
    if isinstance(obj, Timestamp):
        return obj.time
    return obj
