from geolite2 import geolite2

class Executor():

    command = 'geoip'
    use_call_name = True

    def __init__(self, config, debugger):
        self.config = config
        self.debug = debugger
    

    def help(self):
        return ("Geoip:\n"
                f"  {self.command} 1.1.1.1")


    def geolite(self, msg : str) -> str:
        """ Wrapper for geolite. Return data for input IP. """
        reader = geolite2.reader()

        self.debug(f"Performing GeoIP lookup for {msg}")
        result = reader.get(msg)

        if result.get("subdivisions"):
            result = (
                f"```GEO ID: {result['country']['geoname_id']}\n"
                f"COUNTRY: {result['country']['names']['en']}\n"
                f"LATITUDE: {result['location']['latitude']}\n"
                f"LONGITUDE: {result['location']['longitude']}\n"
                f"TIME ZONE: {result['location']['time_zone']}\n"
                f"ISO CODE: {result['subdivisions'][0]['iso_code']}\n"
                f"SUBDIVISION GEO ID: {result['subdivisions'][0]['geoname_id']}\n"
                f"SUBDIVISION: {result['subdivisions'][0]['names']['en']}```")
        else:
            result = (
                f"```GEO ID: {result['country']['geoname_id']}\n"
                f"COUNTRY: {result['country']['names']['en']}\n"
                f"LATITUDE: {result['location']['latitude']}\n"
                f"LONGITUDE: {result['location']['longitude']}```")
        return result


    async def call_executor(self, event, key):
        txt = event.raw_text.replace(key, '').strip()
        result = self.geolite(txt.lower())
        await event.reply(result)