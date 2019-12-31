import itertools
import asyncio

from bson.objectid import ObjectId
from uengine.models.submodel import StorableSubmodel, ShardedSubmodel
from uengine.errors import WrongSubmodel, MissingSubmodel, InputDataError, IntegrityError
from .temp_db_test import TemporaryDatabaseTest


class _BaseTestSubmodel(TemporaryDatabaseTest):
    CLASS = None

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        class TestBaseModel(cls.CLASS):  # pylint: disable=inherit-non-class
            field1 = None
            field2 = None
            __collection__ = "test"

        class Submodel1(TestBaseModel):
            __submodel__ = "submodel1"

        class Submodel2(TestBaseModel):
            __submodel__ = "submodel2"

        TestBaseModel.register_submodel(Submodel1.__submodel__, Submodel1)
        TestBaseModel.register_submodel(Submodel2.__submodel__, Submodel2)

        cls.base_model = TestBaseModel
        cls.submodel1 = Submodel1
        cls.submodel2 = Submodel2
        cls.loop = asyncio.get_event_loop()

    def test_wrong_input(self):
        with self.assertRaises(WrongSubmodel):
            self.submodel1(_id=ObjectId(), field1="value", submodel="wrong")
        with self.assertRaises(MissingSubmodel):
            self.submodel1(_id=ObjectId(), field1="value")
        with self.assertRaises(InputDataError):
            self.submodel1(field1="value", submodel="my_submodel")
        with self.assertRaises(WrongSubmodel):
            obj = self.submodel1(field1="value")
            obj.submodel = "wrong"
            self.loop.run_until_complete(obj.save())

    def test_submodel_field(self):
        obj = self.submodel1()
        self.assertTrue(hasattr(obj, "submodel"))
        self.assertEqual(obj.submodel, self.submodel1.__submodel__)

        self.loop.run_until_complete(obj.save())
        self.loop.run_until_complete(obj.reload())

        self.assertEqual(obj.submodel, self.submodel1.__submodel__)
        db_obj = self.loop.run_until_complete(self.submodel1.get(obj._id))
        self.assertEqual(db_obj.submodel, self.submodel1.__submodel__)

    def test_inheritance(self):
        class Submodel1(self.base_model):
            __submodel__ = "submodel1"

        class Submodel1_1(Submodel1):
            pass

        self.assertEqual(self.base_model.__collection__, Submodel1.__collection__)
        self.assertEqual(Submodel1.__collection__, Submodel1_1.__collection__)
        self.assertEqual(Submodel1.__submodel__, Submodel1_1.__submodel__)

    def test_abstract(self):
        with self.assertRaises(IntegrityError):
            self.base_model()

        with self.assertRaises(IntegrityError):
            class C(self.base_model):
                pass  # no SUBMODEL

            C()

        with self.assertRaises(IntegrityError):
            class C(self.submodel1):
                __submodel__ = "c"

            self.submodel1.register_submodel("c", C)

    def _create_objs(self):
        """Returns two lists of objects. Objects in the same positions only differ in their submodel"""
        values = [1, 2, 3]
        objs1 = [self.submodel1(field1=v, field2=v) for v in values]
        objs2 = [self.submodel2(field1=v, field2=v) for v in values]
        for obj in itertools.chain(objs1, objs2):
           self.loop.run_until_complete(obj.save())

        return objs1, objs2

    def test_isolation_find(self):
        objs1, objs2 = self._create_objs()
        self.assertCountEqual(
            self.loop.run_until_complete(self.submodel1.find().all()),
            objs1,
        )
        self.assertCountEqual(
            self.loop.run_until_complete(self.submodel2.find().all()),
            objs2,
        )
        self.assertCountEqual(
            self.loop.run_until_complete(self.base_model.find().all()),
            objs1 + objs2,
        )

        self.assertCountEqual(
            self.loop.run_until_complete(self.submodel1.find({"field1": objs1[0].field1}).all()),
            [objs1[0]],
        )
        self.assertCountEqual(
            self.loop.run_until_complete(self.base_model.find({"field1": objs1[0].field1}).all()),
            [objs1[0], objs2[0]],
        )


class TestStorableSubmodel(_BaseTestSubmodel):
    CLASS = StorableSubmodel

