from socket import gethostbyname
from typing import Union
import sys
import re


class Executor:

    command = 'getip'
    use_call_name = True

    def __init__(self, config, debugger):
        self.config = config
        self.debug = debugger

    def help(self):
        return "IP Lookup:\n  %s http://website.com" % self.command

    def get_host(self, msg: str) -> Union[str, None]:
        """ Get IP behind a hostname. """
        p = '(?:http.*://)?(?P<host>[^:/ ]+).?(?P<port>[0-9]*).*'
 
        match_host = re.search(p, msg)
        try:
            result = match_host.group('host')
        except:
            return
        try:
            self.debug(f"Performing IP lookup for {result}")
            result = gethostbyname(result)
            return result
        except:
            return "An error has occured: %s" % sys.exc_info()[0]

    async def call_executor(self, event, key):
        txt = event.raw_text.replace(key, '').strip()
        result = self.get_host(txt.lower())
        await event.reply('`'+result+'`')
