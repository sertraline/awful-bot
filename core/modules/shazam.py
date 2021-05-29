from ShazamAPI import Shazam
import asyncio
import uuid
import os


class Executor:

    command = 'shazam'
    use_call_name = False

    def __init__(self, config, debugger, extractor):
        self.config = config
        self.debug = debugger
        self.extractor = extractor

    def help(self):
        return "Shazam:\n  %s <song>" % self.command

    def shazam(self, fname):
        content_to_recognize = open(fname, 'rb').read()

        shazam = Shazam(content_to_recognize)
        recognize_generator = shazam.recognizeSong()
        while True:
            try:
                result = next(recognize_generator)
            except (TypeError, StopIteration):
                return
            if result[1]['matches']:
                track = result[1]['track']
                print(track)

                name = []
                if 'title' in track:
                    name.append(track['title'])
                if 'subtitle' in track:
                    name.append(track['subtitle'])
                name = '> ' + ' — '.join(name)

                cover = None
                if 'images' in track:
                    images = track['images']
                    if 'coverart' in images:
                        cover = images['coverart']

                meta = ""
                sect = track['sections'][0]['metadata']
                try:
                    album = sect[0]
                    album = '> ' + album['text'] + '\n'
                    meta += album
                except:
                    pass
                try:
                    label = sect[1]
                    label = '> ' + label['text'] + '\n'
                    meta += label
                except:
                    pass
                try:
                    year = sect[2]
                    year = '> ' + label['text'] + '\n'
                    meta += year
                except:
                    pass
                return name, cover, meta


    async def call_executor(self, event, client, key):
        self.debug('Call download media')
        fname = str(uuid.uuid4())
        fname = await self.extractor.download_media(event, client, fname)
        if not fname:
            return
        reply = await event.reply("Processing started")
        await client.download_media(event.message, file=fname)
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(None, self.shazam, fname)
        if result:
            msg = "%s\n" % result[0]
            if result[2]:
                msg += (result[2] + '\n')
            if result[1]:
                msg += (result[1] + '\n')
            await reply.delete()
            await event.reply(msg)
        else:
            await reply.edit("Failed to recognize song")
        os.remove(fname)

