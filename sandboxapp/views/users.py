from pydantic import BaseModel, validator
from . import ViewConfig

from sandboxapp.errors import InvalidPassword


class UserSettings(BaseModel):
    Config = ViewConfig
    first_name: str = None
    last_name: str = None
    email: str = None
    avatar: str = None
    mine_filter: bool = None
    docs_per_page: bool = None


class UserView(BaseModel):
    Config = ViewConfig
    first_name: str = None
    last_name: str = None
    email: str = None
    username: str = None


class PasswordFormData(BaseModel):
    Config = ViewConfig
    password_raw: str
    password_raw_confirm: str

    @validator("password_raw_confirm")
    def check_passwords_match(cls, v, values):
        if v != values["password_raw"]:
            raise InvalidPassword("passwords don't match")


class SupervisorFormData(BaseModel):
    Config = ViewConfig
    supervisor: bool


class SystemFormData(BaseModel):
    Config = ViewConfig
    system: bool
