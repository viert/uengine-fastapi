from itertools import chain
from pymongo import ASCENDING, DESCENDING, HASHED
from pymongo.errors import OperationFailure
from bson import ObjectId
from copy import deepcopy
from typing import Any, Iterable, Set, Type, List
from functools import wraps

from .model_hook import ModelHook
from uengine import ctx
from uengine.utils import snake_case
from uengine.errors import FieldRequired, InvalidFieldType


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


class ModelMeta(type):
    def __new__(mcs, name, bases, dct) -> Any:
        new_cls = super().__new__(mcs, name, bases, dct)
        mcs._set_fields(new_cls, dct)
        mcs._set_collection(new_cls, name, bases, dct)

        # First merge mergers config
        merge_dict("__mergers__", new_cls, bases)

        for attr, merge_func in new_cls.__mergers__.items():
            merge_func(attr, new_cls, bases)

        return new_cls

    @staticmethod
    def _set_collection(model_cls, name, bases, dct):
        if '__collection__' in dct:
            model_cls.__collection__ = dct["__collection__"]
        else:
            model_cls.__collection__ = snake_case(name)

    @staticmethod
    def _set_fields(model_cls, dct):
        fields = []
        required = getattr(model_cls, "__required_fields__")
        if required:
            required = set(required)
        else:
            required = set()
        defaults = {}
        types = {}

        if "__annotations__" in dct:
            auxslots = getattr(model_cls, "__auxiliary_slots__", [])
            for attr, value in dct["__annotations__"].items():
                if attr in auxslots:
                    continue
                fields.append(attr)
                types[attr] = value
                if attr in dct:
                    defaults[attr] = dct[attr]
                else:
                    required.add(attr)

        setattr(model_cls, "__fields__", fields)
        setattr(model_cls, "__fields_types__", types)
        setattr(model_cls, "__fields_defaults__", defaults)
        setattr(model_cls, "__required_fields__", required)


class AbstractModel(metaclass=ModelMeta):

    _id: ObjectId = None

    __fields__: Set = None
    __fields_types__: dict = {}
    __fields_defaults__: dict = {}
    __required_fields__: Set = set()
    __rejected_fields__: Set = set()
    __restricted_fields__: Set = set()
    __auto_trim_fields__: Set = set()
    __key_field__: str = None
    __indexes__: (list, tuple) = []
    __hooks__: Set[Type[ModelHook]] = set()

    __auxiliary_slots__: tuple = (
        "__fields__",
        "__fields_types__",
        "__fields_defaults__",
        "__auxiliary_slots__",
        "__rejected_fields__",
        "__required_fields__",
        "__restricted_fields__",
        "__auto_trim_fields__",
        "__key_field__",
        "__indexes__",
        "__mergers__",
        "__hooks__",
    )

    __mergers__: dict = {
        "__fields__": merge_set,
        "__fields_types__": merge_dict,
        "__fields_defaults__": merge_dict,
        "__rejected_fields__": merge_set,
        "__required_fields__": merge_set,
        "__restricted_fields__": merge_set,
        "__auto_trim_fields__": merge_set,
        "__indexes__": merge_tuple,
    }

    def __init__(self, **kwargs):
        # setup in constructor to make linter happy
        self._initial_state = None

        for field, value in kwargs.items():
            if field in self.__fields__:
                setattr(self, field, value)

        for field in self.__fields__:
            if field not in kwargs:
                value = self.__fields_defaults__.get(field)
                if callable(value):
                    value = value()
                elif hasattr(value, "copy"):
                    value = value.copy()
                elif hasattr(value, "__getitem__"):
                    value = value[:]
                setattr(self, field, value)

        self.__set_initial_state()

        self._hook_insts = []
        if self.__hooks__:
            for hook_class in self.__hooks__:
                hook_inst = hook_class.on_model_init(self)
                if hook_inst:
                    self._hook_insts.append(hook_inst)

    @classmethod
    def register_model_hook(cls, model_hook_class: Type[ModelHook], *args, **kwargs) -> None:
        if not issubclass(model_hook_class, ModelHook):
            raise TypeError("Invalid hook class")
        if model_hook_class not in cls.__hooks__:
            cls.__hooks__.add(model_hook_class)
            model_hook_class.on_hook_register(cls, *args, **kwargs)
            ctx.log.debug("Registered hook %s for model %s",
                          model_hook_class.__name__, cls.__name__)

    @classmethod
    def unregister_model_hook(cls, model_hook_class: Type[ModelHook]):
        if model_hook_class in cls.__hooks__:
            cls.__hooks__.remove(model_hook_class)
            model_hook_class.on_hook_unregister(cls)

    @classmethod
    def clear_hooks(cls):
        for hook_class in cls.__hooks__.copy():
            cls.unregister_model_hook(hook_class)

    def __set_initial_state(self):
        setattr(self, "_initial_state", deepcopy(self.to_dict(self.__fields__)))

    def _before_save(self):
        pass

    def _before_validation(self):
        pass

    def _before_delete(self):
        pass

    def _after_save(self, is_new):
        pass

    def _after_delete(self):
        pass

    async def _save_to_db(self):
        pass

    async def _delete_from_db(self):
        pass

    def invalidate(self):
        pass

    @property
    def __missing_fields__(self):
        mfields = []
        for field in self.__required_fields__:
            if not hasattr(self, field) or getattr(self, field) in ["", None]:
                mfields.append(field)
        return mfields

    def _validate(self):
        for field in self.__missing_fields__:
            raise FieldRequired(field)

        for field_name, expected_type in self.__fields_types__.items():
            field = getattr(self, field_name)

            if field is None:
                # This is not a required field otherwise FieldRequired
                # would have raised already. It means the field can be
                # None and thus, have a NoneType instead of what's expected.
                continue

            if not isinstance(field, expected_type):
                raise InvalidFieldType(field_name, field.__class__.__name__, expected_type)

    def _reload_from_obj(self, obj):
        for field in self.__fields__:
            if field == "_id":
                continue
            value = getattr(obj, field)
            setattr(self, field, value)

    async def destroy(self, skip_callback: bool = False, invalidate_cache: bool = True):
        if self.is_new:
            return
        if not skip_callback:
            self._before_delete()
        await self._delete_from_db()
        if not skip_callback:
            self._after_delete()
        self._id = None
        for hook in self.__hooks__:
            try:
                hook.on_model_destroy(self)
            except Exception as e:
                ctx.log.error("error executing destroy hook %s on model %s(%s): %s",
                              hook.__class__.__name__, self.__class__.__name__, self._id, e)
        if invalidate_cache:
            self.invalidate()
        return self

    async def save(self, skip_callback: bool = False, invalidate_cache: bool = True):
        is_new = self.is_new

        if not skip_callback:
            self._before_validation()
        self._validate()

        # autotrim
        for field in self.__auto_trim_fields__:
            print("autotrim", field)
            value = getattr(self, field)
            try:
                value = value.strip()
                setattr(self, field, value)
            except AttributeError:
                pass

        if not skip_callback:
            self._before_save()
        await self._save_to_db()

        for hook in self.__hooks__:
            try:
                hook.on_model_save(self, is_new)
            except Exception as e:
                ctx.log.error("error executing save hook %s on model %s(%s): %s",
                              hook.__class__.__name__, self.__class__.__name__, self._id, e)

        self.__set_initial_state()
        if invalidate_cache:
            self.invalidate()
        if not skip_callback:
            self._after_save(is_new)

        return self

    def __repr__(self):
        attributes = ["%s=%r" % (a, getattr(self, a))
                      for a in list(self.__fields__)]
        return '%s(\n    %s\n)' % (self.__class__.__name__, ',\n    '.join(attributes))

    def __eq__(self, other):
        if self.__class__ != other.__class__:
            return False
        for field in self.__fields__:
            if hasattr(self, field):
                if not hasattr(other, field):
                    return False
                if getattr(self, field) != getattr(other, field):
                    return False
            elif hasattr(other, field):
                return False
        return True

    def __ne__(self, other):
        return not self.__eq__(other)

    @property
    def is_new(self):
        return not(hasattr(self, "_id") and isinstance(self._id, ObjectId))

    @property
    def is_complete(self):
        return len(self.missing_fields) == 0

    def to_dict(self, fields: Iterable[str] = None, include_restricted: bool = False) -> dict:
        if fields is None:
            fields = list(self.__fields__)

        result = {}
        for field in fields:
            if field in self.__restricted_fields__ and not include_restricted:
                continue
            try:
                value = getattr(self, field)
            except AttributeError:
                continue
            if callable(value):
                continue
            result[field] = value
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
                    await db.conn[cls.__collection__].create_index(keys, **options)
                except OperationFailure as e:
                    if e.details.get("codeName") == "IndexOptionsConflict" or e.details.get("code") == 85:
                        if overwrite:
                            if loud:
                                ctx.log.debug(
                                    "Dropping index %s as conflicting", keys)
                            await db.conn[cls.__collection__].drop_index(keys)
                            if loud:
                                ctx.log.debug(
                                    "Creating index with options: %s, %s", keys, options)
                            await db.conn[cls.__collection__].create_index(
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
