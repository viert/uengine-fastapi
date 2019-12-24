from commands import Command
from sandboxapp import app
from uengine import ctx
from uengine.utils import get_modules
import importlib
import os.path
import asyncio


class Index(Command):

    def init_argument_parser(self, parser):
        parser.add_argument("-w", "--overwrite", dest="overwrite", action="store_true", default=False,
                            help="Overwrite existing indexes in case of conflicts")

    async def run_async(self):
        ctx.log.info("Creating indexes")
        models_directory = os.path.join(
            app.base_dir, "sandboxapp/models")
        modules = [x for x in get_modules(models_directory) if x not in
                   ("storable_model", "abstract_model", "sharded_model")]
        for mname in modules:
            module = importlib.import_module(
                "sandboxapp.models.%s" % mname)
            for attr in dir(module):
                if attr.startswith("__") or attr in ("StorableModel", "AbstractModel", "ShardedModel"):
                    continue
                obj = getattr(module, attr)
                if hasattr(obj, "ensure_indexes"):
                    ctx.log.info(
                        "Creating indexes for %s, collection %s", attr, obj.__collection__)
                    await obj.ensure_indexes(True, self.args.overwrite)
        ctx.log.info("Creating sessions indexes")
        ctx.db.meta.conn["sessions"].create_index(
            "sid", unique=True, sparse=False)
