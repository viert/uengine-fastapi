from uengine.models.abstract_model import AbstractModel
from uengine.utils import now
from datetime import datetime
from typing import Iterable


class MyModel(AbstractModel):
    field1: str
    field2: str = "ololo"
    field3: int = 15
    field4: Iterable = []
    created_at: datetime = now

    __required_fields__ = {"field2"}
    __auto_trim_fields__ = {"field2"}

    @property
    def fields_all(self) -> str:
        return f"{self.field1} {self.field2} {self.field3}"


m = MyModel()
print(m.__fields__)
print(m.__fields_defaults__)
print(m.__fields_types__)
print(m.__required_fields__)
m.field1 = "field1"
m._validate()

print(m.fields_all)
print(m.created_at)
print(m)
print(m.__collection__)