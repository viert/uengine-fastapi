from itertools import chain
from pymongo import ASCENDING, DESCENDING, HASHED
from pymongo.errors import OperationFailure
from bson import ObjectId, Timestamp
from pydantic import BaseModel
from typing import Optional, Iterable
from functools import wraps

from uengine import ctx
from .data_types import ObjectIdType


def parse_index_key(index_key):
    if index_key.startswith("-"):
        index_key = index_key[1:]
        order = DESCENDING
    elif index_key.startswith("#"):
        index_key = index_key[1:]
        order = HASHED
    else:
        order = ASCENDING
        if index_key.startswith("+"):
            index_key = index_key[1:]
    return index_key, order


def snake_case(name):
    result = ""
    for i, l in enumerate(name):
        if 65 <= ord(l) <= 90:
            if i != 0:
                result += "_"
            result += l.lower()
        else:
            result += l
    return result


class ObjectSaveRequired(Exception):
    pass


def merge_set(attr, new_cls, bases):
    merged = set()
    valid_types = (list, set, frozenset, tuple)
    for cls in chain(bases, [new_cls]):
        cls_attr = getattr(cls, attr, [])
        if not isinstance(cls_attr, valid_types):
            raise TypeError(
                "{} field must be one of: {}".format(attr, valid_types))
        merged.update(cls_attr)

    setattr(new_cls, attr, frozenset(merged))


def merge_tuple(attr, new_cls, bases):
    merged = []
    for cls in chain(bases, [new_cls]):
        cls_attr = getattr(cls, attr, [])
        if not isinstance(cls_attr, (list, set, tuple)):
            raise TypeError(
                "{} field must be of type list, set or tuple".format(attr))
        merged.extend(cls_attr)
    setattr(new_cls, attr, tuple(merged))


def merge_dict(attr, new_cls, bases):
    merged = {}
    for cls in chain(bases, [new_cls]):
        cls_attr = getattr(cls, attr, {})
        if not isinstance(cls_attr, dict):
            raise TypeError("{} field must be a dict".format(attr))
        merged.update(cls_attr)
    setattr(new_cls, attr, merged)


class AbstractModel(BaseModel):

    class Config:
        from datetime import datetime
        extra = "allow"
        json_encoders = {
            ObjectId: str,
            Timestamp: lambda o: o.time,
            datetime: lambda v: v.timestamp(),
        }

    __collection__: str = None
    __rejected_fields__: set = set()
    __restricted_fields__: set = set()
    __key_field__: str = None
    __indexes__: Iterable = []

    _id: Optional[ObjectIdType] = None

    __mergers__ = {
        "__rejected_fields__": merge_set,
        "__restricted_fields__": merge_set,
        "__indexes__": merge_tuple,
    }

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if "_id" in kwargs:
            self._id = kwargs["_id"]

    def _before_save(self):
        pass

    def _before_delete(self):
        pass

    def _after_save(self, is_new):
        pass

    def _after_delete(self):
        pass

    async def _save_to_db(self):
        pass

    def _delete_from_db(self):
        pass

    def _reload_from_obj(self, obj):
        for field in self.__fields__:
            value = getattr(obj, field)
            setattr(self, field, value)

    def destroy(self, skip_callback=False):
        if self.is_new:
            return
        if not skip_callback:
            self._before_delete()
        self._delete_from_db()
        if not skip_callback:
            self._after_delete()
        self._id = None
        return self

    async def save(self, skip_callback=False):
        is_new = self.is_new

        if not skip_callback:
            self._before_save()
        await self._save_to_db()

        if not skip_callback:
            self._after_save(is_new)

        return self

    @classmethod
    def get_collection_name(cls):
        if cls.__collection__ is None:
            cls.__collection__ = snake_case(cls.__name__)
        return cls.__collection__

    @property
    def is_new(self):
        return not(hasattr(self, "_id") and isinstance(self._id, ObjectId))

    def __repr__(self):
        return f"<{self.__class__.__name__} {super().__str__()}>"

    def to_dict(self, fields=None, include_restricted=False):
        exclude = None if include_restricted else self.__restricted_fields__
        result = self.dict(exclude=exclude)
        result["_id"] = self._id
        if fields:
            filtered = {}
            for field in fields:
                if field in result:
                    filtered[field] = result[field]
            return filtered
        return result

    @classmethod
    def from_data(cls, **data):
        return cls(**data)

    @classmethod
    def _get_possible_databases(cls):
        return [ctx.db.meta]

    @classmethod
    async def ensure_indexes(cls, loud=False, overwrite=False):  # pylint: disable=too-many-branches
        if not isinstance(cls.__indexes__, (list, tuple)):
            raise TypeError("INDEXES field must be of type list or tuple")

        for index in cls.__indexes__:
            if isinstance(index, str):
                index = [index]
            keys = []
            options = {"sparse": False}

            for sub_index in index:
                if isinstance(sub_index, str):
                    keys.append(parse_index_key(sub_index))
                else:
                    for key, value in sub_index.items():
                        options[key] = value
            if loud:
                ctx.log.debug(
                    "Creating index with options: %s, %s", keys, options)

            for db in cls._get_possible_databases():
                try:
                    await db.conn[cls.get_collection_name()].create_index(keys, **options)
                except OperationFailure as e:
                    if e.details.get("codeName") == "IndexOptionsConflict" or e.details.get("code") == 85:
                        if overwrite:
                            if loud:
                                ctx.log.debug(
                                    "Dropping index %s as conflicting", keys)
                            await db.conn[cls.get_collection_name()].drop_index(keys)
                            if loud:
                                ctx.log.debug(
                                    "Creating index with options: %s, %s", keys, options)
                            await db.conn[cls.get_collection_name()].create_index(
                                keys, **options)
                        else:
                            ctx.log.error(
                                "Index %s conflicts with an existing one, use overwrite param to fix it", keys
                            )


def save_required(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        this = args[0]
        if this.is_new:
            raise ObjectSaveRequired("This object must be saved first")
        return func(*args, **kwargs)
    return wrapper
