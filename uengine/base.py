import os
import sys
import inspect
import logging

from logging.handlers import WatchedFileHandler

from . import ctx
from .db import DB

ENVIRONMENT_TYPES = ("development", "testing", "production")
DEFAULT_ENVIRONMENT_TYPE = "development"
DEFAULT_SESSION_EXPIRATION_TIME = 86400 * 7 * 2
DEFAULT_TOKEN_TTL = 86400 * 7 * 2
DEFAULT_LOG_FORMAT = "[%(asctime)s] %(levelname)s %(filename)s:%(lineno)d %(request_id)s %(message)s"
DEFAULT_LOG_LEVEL = "debug"
DEFAULT_FILECACHE_DIR = "/var/cache/uengine"


class Base:

    def __init__(self):
        class_file = inspect.getfile(self.__class__)
        self.app_dir = os.path.dirname(os.path.abspath(class_file))
        self.base_dir = os.path.abspath(os.path.join(self.app_dir, "../"))

        self.version = "development"
        self.__set_version()

        envtype = os.getenv("UENGINE_ENV", DEFAULT_ENVIRONMENT_TYPE)
        if envtype not in ENVIRONMENT_TYPES:
            envtype = DEFAULT_ENVIRONMENT_TYPE
        ctx.envtype = envtype

        self.session_expiration_time = None
        self.session_auto_cleanup = None
        self.session_auto_cleanup_trigger = None

        # Later steps depend on the earlier ones. The order is important here
        ctx.cfg = self.__read_config()
        ctx.log = self.__setup_logging()  # Requires ctx.cfg
        ctx.db = DB()  # Requires ctx.cfg
        self.server = self.__setup_server()
        self.__setup_error_handling()
        ctx.cache = self.__setup_cache()  # requires ctx.cfg and ctx.log
        self.__setup_sessions()
        self.configure_routes()
        self.after_configured()

    def configure_routes(self):
        pass

    def after_configured(self):
        pass

    def __set_version(self):
        ver_filename = os.path.join(self.base_dir, "__version__")
        if not os.path.isfile(ver_filename):
            return
        with open(ver_filename) as verf:
            self.version = verf.read().strip()

    @staticmethod
    def __setup_cache():
        ctx.log.error("CACHE NOT IMPLEMENTED")

    @staticmethod
    def __setup_logging():
        # TODO consider using async logging
        logger = logging.getLogger("app")
        logger.propagate = False

        log_level = ctx.cfg.get("log_level", DEFAULT_LOG_LEVEL)
        log_level = log_level.upper()
        log_level = getattr(logging, log_level)

        if "log_file" in ctx.cfg:
            handler = WatchedFileHandler(ctx.cfg.get("log_file"))
            logger.addHandler(handler)

        if ctx.cfg.get("debug") or not logger.handlers:
            handler = logging.StreamHandler(stream=sys.stdout)
            logger.addHandler(handler)

        log_format = ctx.cfg.get("log_format", DEFAULT_LOG_FORMAT)
        log_format = logging.Formatter(log_format)

        logger.setLevel(log_level)
        for handler in logger.handlers:
            handler.setLevel(log_level)
            handler.setFormatter(log_format)

        logger.info("Logger created, starting up")
        return logger

    @staticmethod
    def __setup_server():
        ctx.log.error("SERVER SETUP NOT IMPLEMENTED")
        pass

    def __read_config(self):
        config_filename = os.path.join(
            self.base_dir, "config", "%s.py" % ctx.envtype)
        with open(config_filename) as f:
            config = {}
            text = f.read()
            code = compile(text, config_filename, 'exec')
            exec(code, config)  # pylint: disable=exec-used
            del config["__builtins__"]
            return config

    def __setup_error_handling(self):
        ctx.log.error("ERROR HANDLING NOT IMPLEMENTED")

    def run(self, **kwargs):
        ctx.log.error("APP RUN NOT IMPLEMENTED")

    def __setup_sessions(self):
        ctx.log.error("SESSIONS NOT IMPLEMENTED")
