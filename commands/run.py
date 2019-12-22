from commands import Command


class Run(Command):

    def run(self):
        from sandboxapp import app
        app.run()

    async def run_async(self):
        pass
