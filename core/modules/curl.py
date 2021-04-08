import urllib.request

class Executor():

    command = 'curl'
    use_call_name = True

    def __init__(self, config, debugger):
        self.config = config
        self.debug = debugger
    

    def help(self):
        return ("Curl -I:\n"
                f"  {self.command} http://website.com/")


    def curl(self, url : str) -> list:
        """ Curl -I: show document info (headers) """
        try:
            if not (url.startswith("http://") or url.startswith("https://")):
                url = "http://"+url

            self.debug(f"GET {url}")
            req = urllib.request.Request(
                url,
                data=None,
                headers={
                    'User-Agent': ("Mozilla/5.0 (Macintosh; "
                                   "Intel Mac OS X 10_9_3) "
                                   "AppleWebKit/537.36 (KHTML, like Gecko) "
                                   "Chrome/35.0.1916.47 Safari/537.36")
                }
            )
            response = urllib.request.urlopen(req)
            response = str(response.info()).splitlines()
            response = [i for i in response if "set-cookie:" not in i.lower()]
            return response
        except urllib.error.HTTPError as e:
            return (f"```An error has occurred: {e}.\n"
                    f"The response code was {e.getcode()}```")


    async def call_executor(self, event, key):
        _user_text = event.raw_text.replace(key, '').strip()
        get_curl = self.curl(_user_text)
        await event.reply(f"```{get_curl}```")