from pydantic import BaseModel
from . import ViewConfig


class WorkGroupView(BaseModel):
    name: str = None
    description: str = None
    email: str = None
