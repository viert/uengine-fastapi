from pydantic import BaseModel
from pydantic.dataclasses import dataclass
from . import ViewConfig


@dataclass(config=ViewConfig)
class UserSettings(BaseModel):
    first_name: str = None
    last_name: str = None
    email: str = None
    avatar: str = None
    mine_filter: bool = None
    docs_per_page: bool = None


@dataclass(config=ViewConfig)
class AuthForm(BaseModel):
    username: str = None
    password: str = None
