import youtube_dl
import os
from asyncio import sleep
import sys
import uuid

class Executor():

    command = 'youdl'
    use_call_name = False

    LENGTH = 1800
    # max. video length, seconds

    def __init__(self, config, debugger):
        self.config = config
        self.debug = debugger


    def help(self):
        return ("Youtube-dl:\n"
            f"  {self.command} http://link.to/thevideo\n"
            f"  {self.command} 360 http://link.to/thevideo\n"
            "  Will download video in 360p\n"
            "Available quality: 360/480/720\n\n")


    async def you_dl(self, event, client, args : list):
        """
        Generate random filename. Check for video quality and duration.
        Return if duration > self.LENGTH//60 mins.
        Download video, upload directly (if server_path and url are empty),
        or move the video to specified path and return the url.
        """
        setname = uuid.uuid4().hex
        path = os.path.dirname(os.path.abspath(__file__))
        filepath = os.path.join(path, str(setname)+".mp4")

        server_path = self.config.SERVER_PATH
        url = self.config.URL

        av_qual = ["360", "480", "720"]

        quality = None
        for arg in args:
            if arg in av_qual:
                quality = arg
            if 'youtube' in arg:
                youlink = arg

        if "&list=" in youlink:
            findlink = youlink.find("&list=")
            youlink = youlink[:findlink]

        if not quality:
            self.debug("No quality specified, using bestvideo+bestaudio")
            ydl_opts = {
                'outtmpl': filepath,
                'format': ('bestvideo[ext=mp4]+bestaudio[ext=m4a]'
                            '/bestvideo+bestaudio')
            }
        else:
            self.debug(f"Quality: {quality}")
            ydl_opts = {
                'outtmpl': filepath,
                'format': (f'bestvideo[height<={quality}][ext=mp4]'
                            f'+bestaudio[ext=m4a]/[height <=? {quality}]'
                            '/bestvideo+bestaudio')
            }

        msg = None
        try:
            with youtube_dl.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(youlink, download=False)
                if int(info['duration']) > self.LENGTH:
                    await event.reply(('Sorry, your video is too long. '
                                       f'Maximum length is {self.LENGTH//60} minutes.'))
                    return
                msg = await event.reply('Download started')
                ydl.download([youlink])
        except:
            await event.reply(('An error has occured. '
                               'Probably, your video is not available.'))

        while not os.path.isfile(filepath):
            await sleep(0.5)

        if not server_path or not url:
            self.debug('Direct upload')
            await client.edit_message(event.message.to_id, msg.id,
                                      'Uploading...')
            await event.reply(file=filepath)
            await client.delete_messages(event.message.to_id, msg.id)
            os.remove(filepath)
            return

        # move file to server directory, send a link to download
        new_dir = os.path.join(server_path, str(setname)+'.mp4')
        os.rename(filepath, new_dir)
        link = f'{url}/{setname}.mp4'
        self.debug(f'Moved: {new_dir} with link: {url}/{setname}.mp4')

        await event.reply(f'Link: {link}')
        await client.delete_messages(event.message.to_id, msg.id)


    async def call_executor(self, event, client, key):
        args = event.raw_text.split(' ')
        if len(args) < 2:
            return
        await self.you_dl(event, client, args[1:])
