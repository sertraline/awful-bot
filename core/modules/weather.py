import asyncio
from pyowm.owm import OWM
from datetime import datetime


class Executor:

    command = 'weather'
    use_call_name = True

    CLEARASCII = [r"     \   /     ",
                  r"      .-.      ",
                  r"   ― (   ) ―   ",
                  r"      '-’      ",
                  r"     /   \     "]
    CLOUDASCII = [r"    \  /       ",
                  r" __ /‘‘.-.     ",
                  r"    \_(   ).   ",
                  r"    /(___(__)  ",
                  r"               "]
    OTHERASCII = [r"      .-.      ",
                  r"     (   ).    ",
                  r"    (___(__)   ",
                  r"   ‚‘‚‘‚‘‚‘    ",
                  r"   ‚’‚’‚’‚’    "]

    def __init__(self, config, debugger):
        self.config = config
        self.debug = debugger
        self.api = OWM(self.config.OWM)

    def help(self):
        return (f"Weather:\n"
                f"  {self.command} Moscow")

    def getweather(self, city: str, owm) -> str:
        if city:
            print(f'Get weather at %s' % city)
            mgr = owm.weather_manager()
            getweather = mgr.weather_at_place(city)
            w = getweather.to_dict()
            w = w['weather']
            wtime = w['reference_time']
            wtime = datetime.utcfromtimestamp(wtime).strftime('%Y-%m-%d %H:%M')
            wind, humidity, sunrise, sunset, temp, status = w['wind'], w['humidity'], w['sunrise_time'], w['sunset_time'], getweather.weather.temperature('celsius'), w['detailed_status']
            sunrise = datetime.utcfromtimestamp(sunrise).strftime('%Y-%m-%d %H:%M')
            sunset = datetime.utcfromtimestamp(sunset).strftime('%Y-%m-%d %H:%M')
            replyascii = self.CLEARASCII if ("clear" or "sunny") in status else self.OTHERASCII
            replyascii = self.CLOUDASCII if "cloud" in status else replyascii
            self.debug(f"Return weather at {city}")
            return(
                f"```​\n{replyascii[0]}{city}:\n"
                f"{replyascii[1]} TEMP: {temp['temp']}°C, {status}\n"
                f"{replyascii[2]} HUM: {humidity}%  WIND: {wind['speed']} m/s\n"
                f"{replyascii[3]} ◓ SUNRISE: {sunrise}\n"
                f"{replyascii[4]} ◒ SUNSET: {sunset}```")
        else:
            return "No city was set!"

    async def call_executor(self, event, key):
        city = event.raw_text.replace(key, '').strip()
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(None, self.getweather, *(city, self.api))
        await event.reply(result)
