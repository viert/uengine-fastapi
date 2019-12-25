import asyncio
from uengine import ctx
from uengine.models.sharded_model import ShardedModel, MissingShardId
from .temp_db_test import TemporaryDatabaseTest

CALLABLE_DEFAULT_VALUE = 4


def callable_default():
    return CALLABLE_DEFAULT_VALUE


class TestModel(ShardedModel):

    field1: str = "default_value"
    field2: str
    field3 = "required_default_value"
    callable_default_field: int = callable_default

    __required_fields__ = {
        "field2",
        "field3",
    }

    __rejected_fields__ = {
        "field1",
    }

    __indexes__ = (
        "field1",
    )


class TestShardedModel(TemporaryDatabaseTest):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.loop = asyncio.get_event_loop()

    def setUp(self):
        super().setUp()
        for shard_id in ctx.db.shards:
            TestModel.destroy_all(shard_id)

    def tearDown(self):
        for shard_id in ctx.db.shards:
            TestModel.destroy_all(shard_id)
        super().tearDown()

    def test_init(self):
        model = TestModel(field1="value")
        self.assertEqual(model.field1, "value")
        model._before_delete()
        model._before_save()

    def test_shard(self):
        model = TestModel(field2="value")
        self.assertIsNone(model._shard_id)
        with self.assertRaises(MissingShardId):
            self.loop.run_until_complete(model.save())

        shard_id = ctx.db.rw_shards[0]
        model = TestModel(shard_id=shard_id, field2="value")
        self.assertEqual(model._shard_id, shard_id)
        self.loop.run_until_complete(model.save())
