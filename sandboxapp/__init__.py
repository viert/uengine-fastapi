import os

from lazy_object_proxy import Proxy
from uengine.base import Base
from uengine import ctx

from sandboxapp.routers.api.v2.users import users
from sandboxapp.routers.api.v2.account import account
from sandboxapp.routers.api.v2.work_groups import work_groups


class App(Base):

    def configure_routes(self):
        ctx.log.info("configuring routes")
        self.server.include_router(users, prefix="/api/v2/users", tags=["users"])
        self.server.include_router(account, prefix="/api/v2/account", tags=["account"])
        self.server.include_router(work_groups, prefix="/api/v2/work_groups", tags=["workgroups"])

    def get_session_class(self):
        from sandboxapp.models import Session
        return Session


def force_init_app():
    _ = app.__doc__  # Doing anything with the app triggers Proxy and creates the real object


app = Proxy(App)
