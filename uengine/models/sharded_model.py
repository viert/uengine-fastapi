from bson.objectid import ObjectId
from functools import partial
from uengine import ctx
from uengine.errors import ApiError, NotFound, MissingShardId
from uengine.utils import resolve_id

from .storable_model import StorableModel


class ShardedModel(StorableModel):

    def __init__(self, **kwargs):
        self._shard_id = None
        if "shard_id" in kwargs:
            self._shard_id = kwargs["shard_id"]
            del kwargs["shard_id"]
        super().__init__(**kwargs)
        if not self.is_new and self._shard_id is None:
            from traceback import print_stack
            print_stack()
            raise MissingShardId(
                "ShardedModel from database with missing shard_id - this must be a bug"
            )

    @property
    def _db(self):
        return ctx.db.shards[self._shard_id]

    async def save(self, skip_callback: bool = False, invalidate_cache: bool = True):
        if self._shard_id is None:
            raise MissingShardId("ShardedModel must have shard_id set before save")
        await super().save(skip_callback=skip_callback, invalidate_cache=invalidate_cache)

    async def _refetch_from_db(self):
        return await self.find_one(self._shard_id, {"_id": self._id})

    @classmethod
    def _get_possible_databases(cls):
        return list(ctx.db.shards.values())

    @classmethod
    def find(cls, shard_id, query=None, **kwargs):
        if not query:
            query = {}
        return ctx.db.get_shard(shard_id).get_objs(
            cls.from_data,
            cls.__collection__,
            cls._preprocess_query(query),
            **kwargs
        )

    @classmethod
    def find_projected(cls, shard_id, query=None, projection=('_id',), **kwargs):
        if not query:
            query = {}
        return ctx.db.get_shard(shard_id).get_objs_projected(
            cls.__collection__,
            cls._preprocess_query(query),
            projection=projection,
            **kwargs
        )

    @classmethod
    async def find_one(cls, shard_id, query, **kwargs):
        return await ctx.db.get_shard(shard_id).get_obj(
            cls.from_data,
            cls.__collection__,
            cls._preprocess_query(query),
            **kwargs
        )

    @classmethod
    async def get(cls, shard_id, expression, raise_if_none=None):
        if expression is None:
            return None

        expression = resolve_id(expression)
        if isinstance(expression, ObjectId):
            query = {"_id": expression}
        else:
            expression = str(expression)
            query = {cls.__key_field__: expression}
        res = await cls.find_one(shard_id, query)
        if res is None and raise_if_none is not None:
            if isinstance(raise_if_none, Exception):
                raise raise_if_none
            else:
                raise NotFound(f"{cls.__name__} not found")
        return res

    # @classmethod
    # def _cache_get(cls, cache_key, getter, constructor=None):
    #     d1 = datetime.now()
    #     if not constructor:
    #         constructor = cls.from_data
    #
    #     if req_cache_has_key(cache_key):
    #         data = req_cache_get(cache_key)
    #         td = (datetime.now() - d1).total_seconds()
    #         ctx.log.debug("ModelCache L1 HIT %s %.3f seconds", cache_key, td)
    #         return constructor(**data)
    #
    #     if ctx.cache.has(cache_key):
    #         data = ctx.cache.get(cache_key)
    #         req_cache_set(cache_key, data)
    #         td = (datetime.now() - d1).total_seconds()
    #         ctx.log.debug("ModelCache L2 HIT %s %.3f seconds", cache_key, td)
    #         return constructor(**data)
    #
    #     obj = getter()
    #     if obj:
    #
    #         data = obj.to_dict()
    #         ctx.cache.set(cache_key, data)
    #         req_cache_set(cache_key, data)
    #
    #     td = (datetime.now() - d1).total_seconds()
    #     ctx.log.debug("ModelCache MISS %s %.3f seconds", cache_key, td)
    #     return obj

    # @classmethod
    # def cache_get(cls, expression, raise_if_none=None):
    #     if expression is None:
    #         return None
    #     cache_key = f"{cls.collection}.{expression}"
    #     getter = partial(cls.get, expression, raise_if_none)
    #     return cls._cache_get(cache_key, getter)

    @staticmethod
    def _invalidate(cache_key_id, cache_key_keyfield=None):
        pass
    #     ctx.log.debug("ModelCache DELETE %s", cache_key_id)
    #     cr_layer1_id = req_cache_delete(cache_key_id)
    #     cr_layer2_id = ctx.cache.delete(cache_key_id)
    #     cr_layer1_keyfield = None
    #     cr_layer2_keyfield = None
    #     if cache_key_keyfield:
    #         ctx.log.debug("ModelCache DELETE %s", cache_key_keyfield)
    #         cr_layer1_keyfield = req_cache_delete(cache_key_keyfield)
    #         cr_layer2_keyfield = ctx.cache.delete(cache_key_keyfield)
    #
    #     return cr_layer1_id, cr_layer1_keyfield, cr_layer2_id, cr_layer2_keyfield

    def invalidate(self):
        cache_key_id = f"{self.__collection__}.{self._shard_id}.{self._id}"
        cache_key_keyfield = None
        if self.__key_field__ is not None and self.__key_field__ != "_id":
            cache_key_keyfield = f"{self.__collection__}.{self._shard_id}.{getattr(self, self.__key_field__)}"

        return self._invalidate(cache_key_id, cache_key_keyfield)

    @classmethod
    async def destroy_all(cls, shard_id):
        # warning: being a faster method than traditional model manipulation,
        # this method doesn't provide any lifecycle callback for independent
        # objects
        await ctx.db.get_shard(shard_id).delete_query(
            cls.__collection__, cls._preprocess_query({}))

    @classmethod
    async def destroy_many(cls, shard_id, query):
        # warning: being a faster method than traditional model manipulation,
        # this method doesn't provide any lifecycle callback for independent
        # objects
        await ctx.db.get_shard(shard_id).delete_query(
            cls.__collection__, cls._preprocess_query(query))

    @classmethod
    async def update_many(cls, shard_id, query, attrs):
        # warning: being a faster method than traditional model manipulation,
        # this method doesn't provide any lifecycle callback for independent
        # objects
        await ctx.db.get_shard(shard_id).update_query(
            cls.__collection__, cls._preprocess_query(query), attrs)
