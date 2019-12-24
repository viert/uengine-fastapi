import asyncio
from uengine.models.storable_model import StorableModel
from .mongo_mock import TempDatabaseTest

CALLABLE_DEFAULT_VALUE = 4


def callable_default():
    return CALLABLE_DEFAULT_VALUE


class TestModel(StorableModel):

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


class TestStorableModel(TempDatabaseTest):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.loop = asyncio.get_event_loop()

    def setUp(self):
        super().setUp()
        self.loop.run_until_complete(TestModel.destroy_all())

    def test_eq(self):
        model = TestModel(field2="mymodel")
        self.loop.run_until_complete(model.save())
        model2 = self.loop.run_until_complete(TestModel.find_one({"field2": "mymodel"}))
        self.assertEqual(model, model2)

    def test_reject_on_update(self):
        model = TestModel(field1="original_value", field2="mymodel_reject_test")
        self.loop.run_until_complete(model.save())
        id_ = model._id
        self.loop.run_until_complete(model.update({"field1": "new_value"}))
        model = self.loop.run_until_complete(TestModel.find_one({"_id": id_}))
        self.assertEqual(model.field1, "original_value")

    def test_update(self):
        model = TestModel(field1="original_value", field2="mymodel_update_test")
        self.loop.run_until_complete(model.save())
        id_ = model._id
        self.loop.run_until_complete(model.update({"field2": "mymodel_updated"}))
        model = self.loop.run_until_complete(TestModel.find_one({"_id": id_}))
        self.assertEqual(model.field2, "mymodel_updated")

    def test_update_many(self):
        model1 = TestModel(field1="original_value", field2="mymodel_update_test")
        self.loop.run_until_complete(model1.save())
        model2 = TestModel(field1="original_value", field2="mymodel_update_test")
        self.loop.run_until_complete(model2.save())
        model3 = TestModel(field1="do_not_modify", field2="mymodel_update_test")
        self.loop.run_until_complete(model3.save())

        self.loop.run_until_complete(
            TestModel.update_many({"field1": "original_value"}, {"$set": {"field2": "mymodel_updated"}})
        )
        self.loop.run_until_complete(model1.reload())
        self.loop.run_until_complete(model2.reload())
        self.loop.run_until_complete(model3.reload())

        self.assertEqual(model1.field2, "mymodel_updated")
        self.assertEqual(model2.field2, "mymodel_updated")
        self.assertEqual(model3.field2, "mymodel_update_test")
