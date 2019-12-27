from pydantic import BaseModel
from typing import List
from . import ViewConfig


class WorkGroupView(BaseModel):
    name: str = None
    description: str = None
    email: str = None


class Owner(BaseModel):
    owner_id: str


class Members(BaseModel):
    member_ids: List[str]
