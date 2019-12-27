from pydantic import BaseModel
from typing import List
from . import ViewConfig


class WorkGroupView(BaseModel):
    Config = ViewConfig
    name: str = None
    description: str = None
    email: str = None


class Owner(BaseModel):
    Config = ViewConfig
    owner_id: str


class Members(BaseModel):
    Config = ViewConfig
    member_ids: List[str]
