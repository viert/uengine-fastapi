from uengine.models.abstract_model import AbstractModel, ObjectIdType
from unittest import TestCase
from pydantic.error_wrappers import ValidationError

CALLABLE_DEFAULT_VALUE = 4


def callable_default():
    return CALLABLE_DEFAULT_VALUE


class TestModel(AbstractModel):

    _id: ObjectIdType = None
    field1: str = 'default_value'
    field2: str
    field3: str = 'required_default_value'

    __rejected_fields__ = ("field1",)
    __indexes__ = ("field1",)


class TestAbstractModel(TestCase):

    def test_init(self):
        model = TestModel(field2="value2")
        self.assertEqual(model.field2, "value2")
        self.assertEqual(model.field1, 'default_value')
        model._before_delete()
        model._before_save()

    def test_incomplete(self):
        with self.assertRaises(ValidationError):
            _ = TestModel(field1="value")

    def test_collection_inheritance(self):
        class SemiAbstractModel(AbstractModel):
            pass

        class BaseModel(SemiAbstractModel):
            __collection__ = "my_collection"

        class Model1(BaseModel):
            pass

        self.assertEqual(SemiAbstractModel.get_collection_name(), "semi_abstract_model")
        self.assertEqual(BaseModel.get_collection_name(), "my_collection")
        self.assertEqual(Model1.get_collection_name(), "model1")