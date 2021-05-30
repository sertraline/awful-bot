import aiohttp
import json
import random
import traceback
import re


class Executor:
    command = 'youtube'
    use_call_name = False

    __url = 'https://www.youtube.com/results'

    def __init__(self, config, debugger):
        self.config = config
        self.debug = debugger

    def help(self):
        return "Youtube search: \n %s <song name>" % self.command

    async def search(self, name):

        params = {
            'search_query': name
        }
        headers = {
            'User-Agent': 'Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)'
        }
        cookies = {
            'CONSENT': 'YES+cb.20210328-17-p0.en-GB+FX+{}'.format(random.randint(100, 999))
        }

        async with aiohttp.ClientSession(headers=headers, cookies=cookies) as session:
            async with session.get(self.__url, params=params) as r:
                if r.status != 200:
                    self.debug('Youtube search: %d' % r.status)
                    return

                resp = await r.text()
                data = re.findall(r'var ytInitialData = ({.*?});', resp)
                if not data:
                    self.debug('Youtube search: no data')
                    return

                js = json.loads(data[0])
                renderer = js['contents']['twoColumnSearchResultsRenderer']['primaryContents']['sectionListRenderer']
                contents = renderer['contents'][0]['itemSectionRenderer']['contents']

                results = ''
                for content in contents[:6]:
                    if 'videoRenderer' in content:
                        renderer = content['videoRenderer']
                        video_id = renderer['videoId']
                        title = renderer['title']['runs'][0]['text']
                        length = renderer['lengthText']['simpleText']
                        result = '%s [%s]\n%s\n' % (title, length, 'https://youtube.com/watch?v=' + video_id)
                        results += result
                    elif 'playlistRenderer' in content:
                        renderer = content['playlistRenderer']
                        playlist_id = renderer['playlistId']
                        title = renderer['title']['simpleText']
                        count = renderer['videoCount']
                        endp = renderer['videos'][0]['childVideoRenderer']['navigationEndpoint']['watchEndpoint']
                        video_id = endp['videoId']

                        playlist_url = ('https://youtube.com/watch?v=' + video_id + '&list=' + playlist_id)
                        result = '%s [%s items]\n%s\n' % (title, count, playlist_url)
                        results += result

                return results

    async def call_executor(self, event):
        message = event.raw_text.replace('%syoutube' % self.config.S, '').strip()
        if not message:
            return

        result = None
        try:
            result = await self.search(message)
        except:
            self.debug(traceback.format_exc())
            pass

        if result:
            await event.reply(result)
        else:
            await event.reply("No results for this query.")
