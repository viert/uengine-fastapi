import os

from lazy_object_proxy import Proxy
from uengine.base import Base
from uengine import ctx


class App(Base):

    def configure_routes(self):
        ctx.log.info("configuring routes")


def force_init_app():
    _ = app.__doc__  # Doing anything with the app triggers Proxy and creates the real object


app = Proxy(App)
