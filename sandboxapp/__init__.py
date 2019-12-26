import os

from lazy_object_proxy import Proxy
from uengine.base import Base
from uengine import ctx

from sandboxapp.routers.api.v1.users import users
from sandboxapp.routers.api.v1.account import account


class App(Base):

    def configure_routes(self):
        ctx.log.info("configuring routes")
        self.server.include_router(users, prefix="/api/v1/users", tags=["users"])
        self.server.include_router(account, prefix="/api/v1/account", tags=["account"])

    def get_session_class(self):
        from sandboxapp.models import Session
        return Session


def force_init_app():
    _ = app.__doc__  # Doing anything with the app triggers Proxy and creates the real object


app = Proxy(App)
