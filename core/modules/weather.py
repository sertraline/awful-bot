import pyowm, sys

class Executor():

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
        self.api = pyowm.OWM(self.config.OWM, language='en')


    def help(self):
        return (f"Weather:\n"
                f"  {self.command} Moscow")


    def getweather(self, city : str, owm : pyowm) -> str:
        if city:
            print(f'Get weather at {city}')
            getweather = owm.weather_at_place(city)
            w = getweather.get_weather()
            wtime = w.get_reference_time(timeformat='iso')
            wind, humidity, sunrise, sunset, temp, status = w.get_wind(), w.get_humidity(), w.get_sunrise_time(
            timeformat='iso'), w.get_sunset_time(timeformat='iso'), w.get_temperature('celsius'), w.get_detailed_status()
            replyascii = self.CLEARASCII if ("clear" or "sunny") in status else self.OTHERASCII
            replyascii = self.CLOUDASCII if "cloud" in status else replyascii
            self.debug(f"Return weather at {city}")
            return(
                f"Weather:```{replyascii[0]}{city}:\n"
                f"{replyascii[1]} TEMP: {temp['temp']}°C, {status}\n"
                f"{replyascii[2]} HUM: {humidity}%  WIND: {wind['speed']} m/s\n"
                f"{replyascii[3]} ◓ SUNRISE: {sunrise}\n"
                f"{replyascii[4]} ◒ SUNSET: {sunset}```")
        else:
            return("No city was set!")


    async def call_executor(self, event, key):
        city = event.raw_text.replace(key, '').strip()
        result = self.getweather(city, self.api)
        await event.reply(result)