import asyncio
from string import ascii_lowercase
from random import choice
from unittest import TestCase
from uengine import ctx
from uengine.db import DB

TEMP_DB_PREFIX_LENGTH = 5


class TemporaryDatabaseTest(TestCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        try:
            del ctx.cfg
            del ctx.db
        except AttributeError:
            pass

        key = "".join([choice(ascii_lowercase) for _ in range(TEMP_DB_PREFIX_LENGTH)])
        ctx.cfg = {
            "database": {
                "meta": {
                    "uri": "mongodb://localhost",
                    "dbname": f"unittest_meta_{key}",
                },
                "shards": {
                    "s1": {
                        "uri": "mongodb://localhost",
                        "dbname": f"unittest_s1_{key}",
                    },
                    "s2": {
                        "uri": "mongodb://localhost",
                        "dbname": f"unittest_s2_{key}",
                    },
                }
            }
        }
        ctx.db = DB()

    @classmethod
    def tearDownClass(cls) -> None:
        conns = [ctx.db.meta.conn] + [x.conn for x in ctx.db.shards.values()]
        tasks = [conn.command('dropDatabase') for conn in conns]
        loop = asyncio.get_event_loop()
        loop.run_until_complete(asyncio.gather(*tasks))
