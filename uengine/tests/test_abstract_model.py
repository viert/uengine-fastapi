import asyncio

from uengine.models.abstract_model import AbstractModel
from uengine.errors import FieldRequired, InvalidFieldType
from unittest import TestCase

CALLABLE_DEFAULT_VALUE = 4


def callable_default():
    return CALLABLE_DEFAULT_VALUE


class TestModel(AbstractModel):
    field1: str = "default_value"
    field2: str
    field3 = "field3_default_value"
    callable_default_field: int = callable_default
    __auto_trim_fields__ = ["field1"]


class TestAbstractModel(TestCase):

    @classmethod
    def setUpClass(cls) -> None:
        cls.loop = asyncio.get_event_loop()

    def test_init(self):
        model = TestModel(field1='value')
        self.assertEqual(model.field1, 'value')
        model._before_delete()
        model._before_save()

    def test_incomplete(self):
        model = TestModel(field1='value')
        with self.assertRaises(FieldRequired):
            self.loop.run_until_complete(model.save())

    def test_incorrect_index(self):
        with self.assertRaises(TypeError):
            class IncorrectIndexModel(AbstractModel):  # pylint: disable=unused-variable
                __indexes__ = (
                    "field1"  # No comma - not a tuple
                )

    def test_invalid_type(self):
        model = TestModel(field1=15, field2="any_value")
        with self.assertRaises(InvalidFieldType):
            self.loop.run_until_complete(model.save())

    def test_merge_on_inheritance(self):
        class Parent(AbstractModel):
            pfield: str = "value"
            __required_fields__ = {"pfield"}
            __rejected_fields__ = {"pfield"}
            __restricted_fields__ = {"pfield"}
            __indexes__ = ["pfield"]

        class Child(Parent):
            cfield: str = "value"
            __required_fields__ = {"cfield"}
            __rejected_fields__ = {"cfield"}
            __restricted_fields__ = {"cfield"}
            __indexes__ = ["cfield"]

        expected_fields = {"pfield", "cfield"}
        self.assertSetEqual(Child.__fields__, expected_fields | {"_id"})  # _id comes from AbstractModel
        self.assertSetEqual(Child.__required_fields__, expected_fields)
        self.assertSetEqual(Child.__rejected_fields__, expected_fields)
        self.assertSequenceEqual(sorted(Child.__indexes__), sorted(expected_fields))

        # Unrelated Mixins should also work
        class Mixin:  # pylint: disable=unused-variable
            pass

        class ChildNoOverrides(Mixin, Parent):  # pylint: disable=unused-variable
            pass

    def test_collection_inheritance(self):
        class SemiAbstractModel(AbstractModel):
            pass

        class BaseModel(SemiAbstractModel):
            __collection__ = "my_collection"

        class Model1(BaseModel):
            pass

        self.assertEqual(SemiAbstractModel.__collection__, "semi_abstract_model")
        self.assertEqual(BaseModel.__collection__, "my_collection")
        self.assertEqual(Model1.__collection__, "model1")

    def test_auto_trim(self):
        t = TestModel(field1="   a   \t", field2="b", field3="c")
        self.loop.run_until_complete(t.save())
        self.assertEqual(t.field1, "a")
