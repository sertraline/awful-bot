from random import choice
from copy import deepcopy

class Executor():

    command = 'ping'
    use_call_name = False

    def __init__(self, config, debug):
        self.config = config
        self.debug = debug
        self.dummy = deepcopy(config.PING)
    

    def help(self):
        return f"Ping:\n  {self.command}"


    async def ping(self, event):
        num_choice = choice(range(len(self.dummy)))
        if (len(self.dummy) > 1):
            toprint = self.dummy[num_choice]
            await event.reply(toprint)
            del self.dummy[num_choice]
        else:
            self.dummy = deepcopy(self.config.PING)
            toprint = self.dummy[num_choice]
            await event.reply(toprint)
            del self.dummy[num_choice]
    

    async def call_executor(self, event):
        await self.ping(event)