from bson.objectid import ObjectId, InvalidId
from pydantic import ValidationError


class ObjectIdType(ObjectId):
    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, v):
        if v is None:
            return None
        if isinstance(v, ObjectId):
            return v

        try:
            v = ObjectId(v)
        except InvalidId:
            raise ValidationError(f"ObjectId or corresponding str expected, not {type(v)}")

        return v
