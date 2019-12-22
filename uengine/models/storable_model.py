from .abstract_model import AbstractModel, save_required
from bson.objectid import ObjectId

from uengine import ctx
from uengine.utils import resolve_id
from uengine.errors import NotFound, ModelDestroyed, IntegrityError


class StorableModel(AbstractModel):

    def __init__(self, **kwargs):
        AbstractModel.__init__(self, **kwargs)

    @property
    def _db(self):
        if not self.get_collection_name():
            raise IntegrityError(
                f"There is no DB for abstract model: {self.__class__.__name__}")
        return ctx.db.meta

    async def _save_to_db(self):
        return await self._db.save_obj(self)

    async def update(self, data, skip_callback=False):
        for field in self.__fields__:
            if field in data and field not in self.__rejected_fields__ and field != "_id":
                self.__setattr__(field, data[field])
        await self.save(skip_callback=skip_callback)

    @save_required
    async def db_update(self, update, when=None, reload=True):
        """
        :param update: MongoDB update query
        :param when: filter query. No update will happen if it does not match
        :param reload: Load the new stat into the object (Caution: if you do not do this
                       the next save() will overwrite updated fields)
        :return: True if the document was updated. Otherwise - False
        """
        new_data = await self._db.find_and_update_obj(self, update, when)
        if reload and new_data:
            tmp = self.from_data(**new_data)
            self._reload_from_obj(tmp)

        return bool(new_data)

    async def _delete_from_db(self):
        await self._db.delete_obj(self)

    async def _refetch_from_db(self):
        return await self.find_one({"_id": self._id})

    async def reload(self):
        if self.is_new:
            return
        tmp = await self._refetch_from_db()
        if tmp is None:
            raise ModelDestroyed("model has been deleted from db")
        for field in self.__fields__:
            if field == "_id":
                continue
            value = getattr(tmp, field)
            setattr(self, field, value)

    @classmethod
    # E.g. override if you want model to always return a subset of documents in its collection
    def _preprocess_query(cls, query):
        return query

    @classmethod
    def find(cls, query=None, **kwargs):
        if not query:
            query = {}
        return ctx.db.meta.get_objs(cls.from_data, cls.get_collection_name(), cls._preprocess_query(query), **kwargs)

    @classmethod
    def find_projected(cls, query=None, projection=('_id',), **kwargs):
        if not query:
            query = {}
        return ctx.db.meta.get_objs_projected(cls.get_collection_name(), cls._preprocess_query(query),
                                              projection=projection, **kwargs)

    @classmethod
    async def find_one(cls, query, **kwargs):
        return await ctx.db.meta.get_obj(cls.from_data, cls.get_collection_name(), cls._preprocess_query(query), **kwargs)

    @classmethod
    async def get(cls, expression, raise_if_none=None):
        if expression is None:
            return None

        expression = resolve_id(expression)
        if isinstance(expression, ObjectId):
            query = {"_id": expression}
        else:
            expression = str(expression)
            query = {cls.__key_field__: expression}
        res = await cls.find_one(query)
        if res is None and raise_if_none is not None:
            if isinstance(raise_if_none, Exception):
                raise raise_if_none
            else:
                raise NotFound(f"{cls.__name__} not found")
        return res

    @classmethod
    async def destroy_all(cls):
        await ctx.db.meta.delete_query(cls.get_collection_name(), cls._preprocess_query({}))

    @classmethod
    async def destroy_many(cls, query):
        # warning: being a faster method than traditional model manipulation,
        # this method doesn't provide any lifecycle callback for independent
        # objects
        await ctx.db.meta.delete_query(cls.get_collection_name(), cls._preprocess_query(query))

    @classmethod
    async def update_many(cls, query, attrs):
        # warning: being a faster method than traditional model manipulation,
        # this method doesn't provide any lifecycle callback for independent
        # objects
        await ctx.db.meta.update_query(cls.get_collection_name(), cls._preprocess_query(query), attrs)
