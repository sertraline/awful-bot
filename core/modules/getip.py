from socket import gethostbyname
import sys
import re

class Executor():

    command = 'getip'
    use_call_name = True

    def __init__(self, config, debugger):
        self.config = config
        self.debug = debugger


    def help(self):
        return ("IP Lookup:\n"
                f"  {self.command} http://website.com")


    def get_host(self, msg : str) -> str:
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
            return f"An error occured: {sys.exc_info()[0]}"


    async def call_executor(self, event, key):
        txt = event.raw_text.replace(key, '').strip()
        result = self.get_host(txt.lower())
        await event.reply(f"`{result}`")