from commands import Command


class Run(Command):

    def init_argument_parser(self, parser):
        parser.add_argument("--host", "-H", type=str, dest="host", help="Bind on host", default="127.0.0.1")
        parser.add_argument("--port", "-P", type=int, dest="port", help="Bind on port", default=5000)

    def run(self):
        from sandboxapp import app
        app.run(host=self.args.host, port=self.args.port)

    async def run_async(self):
        pass
