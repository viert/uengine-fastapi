from . import ViewConfig
from pydantic import BaseModel


class AuthForm(BaseModel):
    Config = ViewConfig
    username: str = None
    password: str = None


