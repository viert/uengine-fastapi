import ujson
import json

loads = ujson.loads


def uengine_json_encode(o):
    from bson import ObjectId, Timestamp
    from .models.abstract_model import AbstractModel

    if isinstance(o, ObjectId):
        return str(o)
    if isinstance(o, Timestamp):
        return o.time
    if isinstance(o, AbstractModel):
        return o.to_dict()
    return o


def dumps(obj):
    return json.dumps(obj, default=uengine_json_encode)
