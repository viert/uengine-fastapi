import pymongo
import asyncio
import functools
import inspect

from bson.objectid import ObjectId, InvalidId
from motor.motor_asyncio import AsyncIOMotorClient
from pymongo.errors import ServerSelectionTimeoutError
from uengine.errors import InvalidShardId

from . import ctx
from .models.abstract_model import AbstractModel

CURSOR_BUFFER_LENGTH = 20


def intercept_db_errors_rw(retry_sleep: int = 3, max_retries: int = 6):
    def decorator(func):
        if not inspect.iscoroutinefunction(func):
            raise RuntimeError(f"intercept_db_errors_rw can not decorate synchronous functions {func.__name__}")

        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            if "retries_left" in kwargs:
                retries_left = kwargs["retries_left"]
                del kwargs["retries_left"]
            else:
                retries_left = max_retries

            try:
                result = await func(*args, **kwargs)
            except ServerSelectionTimeoutError:
                ctx.log.error(
                    "ServerSelectionTimeout in db module for read/write operations")
                retries_left -= 1
                if retries_left == max_retries / 2:
                    ctx.log.error(
                        "Mongo connection %d retries passed with no result, "
                        "trying to reinstall connection",
                        max_retries / 2
                    )
                    db_obj = args[0]
                    db_obj.reset_conn()
                if retries_left == 0:
                    ctx.log.error(
                        "Mongo connection %d retries more passed with no result, giving up", max_retries / 2)
                    raise

                await asyncio.sleep(retry_sleep)

                kwargs["retries_left"] = retries_left
                return await wrapper(*args, **kwargs)
            return result

        return wrapper

    return decorator


def intercept_db_errors_ro(retry_sleep: int = 3, max_retries: int = 6):
    def decorator(func):
        if not inspect.iscoroutinefunction(func):
            raise RuntimeError(f"intercept_db_errors_ro can not decorate synchronous functions {func.__name__}")

        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            if "retries_left" in kwargs:
                retries_left = kwargs["retries_left"]
                del kwargs["retries_left"]
            else:
                retries_left = max_retries

            try:
                result = await func(*args, **kwargs)
            except ServerSelectionTimeoutError:
                ctx.log.error(
                    "ServerSelectionTimeout in db module for read/write operations")
                retries_left -= 1
                if retries_left == max_retries / 2:
                    ctx.log.error(
                        "Mongo readonly connection %d retries passed, switching "
                        "readonly operations to read-write socket",
                        max_retries / 2
                    )
                    db_obj = args[0]
                    db_obj._ro_conn = db_obj.conn  # pylint: disable=protected-access
                if retries_left == 0:
                    ctx.log.error(
                        "Mongo connection %d retries more passed with no result, giving up", max_retries / 2)
                    raise

                await asyncio.sleep(retry_sleep)

                kwargs["retries_left"] = retries_left
                return await wrapper(*args, **kwargs)
            return result

        return wrapper

    return decorator


class ObjectsCursor:

    def __init__(self, cursor, obj_constructor, query, shard_id=None):
        self.obj_constructor = obj_constructor
        self.query = query
        self.cursor = cursor
        self.shard_id = shard_id

    @intercept_db_errors_ro()
    async def all(self):
        res = []
        for doc in await self.cursor.to_list(length=CURSOR_BUFFER_LENGTH):
            res.append(self.obj_constructor(**doc))
        return res

    def limit(self, *args, **kwargs):
        self.cursor.limit(*args, **kwargs)
        return self

    def skip(self, *args, **kwargs):
        self.cursor.skip(*args, **kwargs)
        return self

    def sort(self, *args, **kwargs):
        self.cursor.sort(*args, **kwargs)
        return self

    def __aiter__(self):
        return self

    @intercept_db_errors_ro()
    async def __anext__(self):
        has_data = await self.cursor.fetch_next
        if has_data:
            doc = self.cursor.next_object()
            return self.obj_constructor(**doc)
        raise StopAsyncIteration

    def __getattr__(self, item):
        return getattr(self.cursor, item)


class DBShard:
    def __init__(self, dbconf, shard_id=None):
        self._config = dbconf
        self._conn = None
        self._ro_conn = None
        self._shard_id = shard_id

    def reset_conn(self):
        self._conn = None

    def reset_ro_conn(self):
        self._ro_conn = None

    def init_ro_conn(self):
        ctx.log.info("Creating a read-only mongo connection")
        client_kwargs = self._config.get("pymongo_extra", {})
        database = self._config.get('dbname')
        if "uri_ro" in self._config:
            ro_client = AsyncIOMotorClient(self._config["uri_ro"], **client_kwargs)
            self._ro_conn = ro_client[database]
        else:
            ctx.log.info(
                "No uri_ro option found in configuration, falling back to read/write default connection")
            self._ro_conn = self.conn

    def init_conn(self):
        ctx.log.info("Creating a read/write mongo connection")
        client_kwargs = self._config.get("pymongo_extra", {})
        client = AsyncIOMotorClient(self._config["uri"], **client_kwargs)
        database = self._config['dbname']
        self._conn = client[database]

    @property
    def conn(self):
        if self._conn is None:
            self.init_conn()
        return self._conn

    @property
    def ro_conn(self):
        if self._ro_conn is None:
            self.init_ro_conn()
        return self._ro_conn

    @intercept_db_errors_ro()
    async def get_obj(self, cls, collection, query):
        if not isinstance(query, dict):
            try:
                query = {'_id': ObjectId(query)}
            except InvalidId:
                pass
        data = await self.ro_conn[collection].find_one(query)
        if data:
            if self._shard_id:
                data["shard_id"] = self._shard_id
            return cls(**data)
        return None

    @intercept_db_errors_ro()
    async def get_obj_id(self, cls, collection, query):
        if not isinstance(query, dict):
            try:
                query = {'_id': ObjectId(query)}
            except InvalidId:
                pass
        doc = await self.ro_conn[collection].find_one(query, projection=())
        if doc:
            return doc["_id"]
        return None

    def get_objs(self, cls, collection, query, **kwargs):
        cursor = self.ro_conn[collection].find(query, **kwargs)
        return ObjectsCursor(cursor, cls, query, shard_id=self._shard_id)

    def get_objs_projected(self, collection, query, projection, **kwargs):
        cursor = self.ro_conn[collection].find(
            query, projection=projection, **kwargs)
        return cursor

    @intercept_db_errors_rw()
    async def save_obj(self, obj: AbstractModel):
        if obj.is_new:
            data = obj.to_dict(include_restricted=True, jsonable_dict=False)
            del data["_id"]
            result = await self.conn[obj.__collection__].insert_one(data)
            obj._id = result.inserted_id
        else:
            await self.conn[obj.__collection__].replace_one(
                {"_id": obj._id}, obj.to_dict(include_restricted=True, jsonable_dict=False), upsert=True
            )

    @intercept_db_errors_rw()
    async def delete_obj(self, obj):
        if obj.is_new:
            return
        self.conn[obj.__collection__].delete_one({'_id': obj._id})

    @intercept_db_errors_rw()
    async def find_and_update_obj(self, obj, update, when=None):
        query = {"_id": obj._id}
        if when:
            assert "_id" not in when
            query.update(when)

        new_data = await self.conn[obj.__collection__].find_one_and_update(
            query,
            update,
            return_document=pymongo.ReturnDocument.AFTER
        )
        if new_data and self._shard_id:
            new_data["shard_id"] = self._shard_id
        return new_data

    @intercept_db_errors_rw()
    async def delete_query(self, collection, query):
        return await self.conn[collection].delete_many(query)

    @intercept_db_errors_rw()
    async def update_query(self, collection, query, update):
        return await self.conn[collection].update_many(query, update)


class DB:

    def __init__(self):
        self.meta = DBShard(ctx.cfg["database"]["meta"])
        self.shards = {}
        if "shards" in ctx.cfg["database"]:
            for shard_id, config in ctx.cfg["database"]["shards"].items():
                self.shards[shard_id] = DBShard(config, shard_id)

        if "open_shards" in ctx.cfg["database"]:
            self.rw_shards = ctx.cfg["database"]["open_shards"]
        else:
            self.rw_shards = list(self.shards.keys())

    def get_shard(self, shard_id):
        if shard_id not in self.shards:
            raise InvalidShardId(f"shard {shard_id} doesn't exist")
        return self.shards[shard_id]
