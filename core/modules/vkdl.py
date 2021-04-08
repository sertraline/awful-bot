from core import vk_api
from core.vk_api.audio import VkAudio
import aiohttp
import asyncio
import aiofiles
import aiodns
import socket
import zipfile
import traceback
import uuid
import os
import re
from os.path import join
from json.decoder import JSONDecodeError

class Executor():

    command = 'vkdl'
    use_call_name = False

    def __init__(self, config, debugger):
        self.config = config
        self.debug = debugger
        self.vk_session = vk_api.VkApi(self.config.VK_LOGIN,
                                       self.config.VK_PASS)
        try:
            self.debug('VK AUTH')
            self.vk_session.auth()
        except vk_api.AuthError as error_msg:
            self.debug(error_msg)
            return

        self.debug('INIT VkAudio')
        self.audio = VkAudio(self.vk_session, self.debug)


    def help(self):
        return (f'Download audios from VK post:\n'
                f'  {self.config.S}vkdl link_to_wall_post\n'
                f'  In zip format: {self.config.S}vkdl link_to_wall_post zip')


    def create_session(self):
        resolver = aiohttp.AsyncResolver(nameservers=["8.8.8.8",
                                                      "8.8.4.4"])
        return aiohttp.ClientSession(connector=aiohttp.TCPConnector(
                                     ttl_dns_cache=300,
                                     resolver=resolver,
                                     family=socket.AF_INET,
                                     ssl=False))


    async def get_file(self, sess, track_name, track_url,
                       event, client, counter, msg_id, length):
        self.debug(track_url)
        response = await sess.request('get', track_url)
        async for data in response.content.iter_chunked(1024):
            async with aiofiles.open(track_name, "ba") as f:
                await f.write(data)

        # counter: shared dict
        # keep track of files downloaded in total
        counter['c'] += 1
        cc = counter['c']

        await client.edit_message(event.message.to_id, msg_id,
                                  f'Download in progress ({cc}/{length})')
        await sess.close()
        return track_name


    async def user_dl(self, event, client, user_id, arg):
        msg = await event.reply('Started tracks collection')

        if arg:
            if 'zip' in str(arg):
                await client.edit_message(event.message.to_id, msg.id,
                                         ('Started tracks collection\n'
                                         '__zip in user downloads is not '
                                         'supported - using defaults__'))
        count = int(arg) if (arg and arg.isdigit()) else 10
        if not arg:
            await client.edit_message(event.message.to_id, msg.id,
                                    ('Started tracks collection\n'
                                    '__track counter is not specified - '
                                    'using defaults (10 tracks)__')) 
        post = await self.audio.get(user_id, album_id=None, count=count)

        song_list = []

        randname = uuid.uuid4().hex
        if not os.path.isdir(randname):
            os.mkdir(randname)

        # strip forbidden characters from filename
        remove_punctuation_map = dict((ord(char), None) for char in '\/*?:"<>|')

        # files tracker
        counter = {'c': 0}
        if count:
            length = count
            for i in range(0, count):
                track_name = f"{post[i]['artist']} - {post[i]['title']}.mp3"
                track_name = track_name.translate(remove_punctuation_map)

                track_url = post[i]['url']
                song_list.append([join(randname, track_name), track_url, event,
                                  client, counter, msg.id, length])
        else:
            length = len(post)
            for song in post:
                track_name = f"{song['artist']} - {song['title']}.mp3"
                track_name = track_name.translate(remove_punctuation_map)

                track_url = song['url']
                song_list.append([join(randname, track_name), track_url, event,
                                  client, counter, msg.id, length])

        # uploaded files tracker
        up_cc = 0
        files = []
        futures = [self.get_file(self.create_session(), *args) for args in song_list]
        for future in asyncio.as_completed(futures):
            file = await future
            await client.edit_message(event.message.to_id, msg.id,
                                      f'Uploading... {up_cc}/{len(song_list)}')
            await event.reply(file=file)
            files.append(file)
            up_cc += 1

        if self.config.DELETE_AFTER_UPLOAD:
            for file in files:
                os.remove(file)
            os.rmdir(randname)
        await client.delete_messages(event.message.to_id, msg.id)


    async def post_dl(self, event, client, post_id, arg):
        if not 'access_hash' in post_id and \
            not 'audio_playlist' in post_id and not 'album' in post_id:
            owner, post_id = post_id.split('_')
            post = await self.audio.get_post_audio(owner, post_id)
        else:
            owner_id, album_id, access_hash = (None for i in range(3))

            parts = re.findall((r'audio_playlist(\d+)_'
                                r'(\d+).*?access_hash=(.*)'), post_id)
            if parts:
                owner_id, album_id, access_hash = parts[0]
                self.debug(f'{owner_id}, {album_id}, {access_hash}')
                post = await self.audio.get(owner_id, album_id, access_hash)
            else:
                if '%2F' in post_id:
                    post_id = post_id.replace('%2F', '/')

                parts = re.findall((r'audio_playlist(-?\d+)_(\d+)'), post_id)
                if parts:
                    owner_id, album_id = parts[0]
                    if not post_id.endswith(album_id):
                        find_hash = post_id.rfind('/')
                        if find_hash != -1:
                            access_hash = post_id[find_hash:].strip('/')
                    else:
                        access_hash = None

                    self.debug(f'{owner_id}, {album_id}, {access_hash}')
                    post = await self.audio.get(owner_id, album_id, access_hash)
                else:
                    check = post_id.find('audio_playlist')
                    if check != -1:
                        pl = post_id[check+len('audio_playlist'):]
                        owner_id, album_id = pl.split('_')
                        access_hash = None
                    else:
                        check = post_id.find('music/album/')
                        if check != -1:
                            pl = post_id[check+len('music/album/'):]
                            owner_id, album_id, *access_hash = pl.split('_')
                            access_hash = None if not access_hash else access_hash[0]
                    self.debug(f'{owner_id}, {album_id}, {access_hash}')
                    post = await self.audio.get(owner_id, album_id, access_hash)

        length = len(post)
        msg = await event.reply(f'Download in progress (0/{length})')

        randname = uuid.uuid4().hex
        if not os.path.isdir(randname):
            os.mkdir(randname)

        par_list = []
        counter = {'c': 0}

        remove_punctuation_map = dict((ord(char), None) for char in '\/*?:"<>|')

        for track in post:
            artist = track['artist']
            title = track['title']

            track_name = f'{artist} - {title}.mp3'
            track_name = track_name.translate(remove_punctuation_map)
            track_name = join(randname, track_name)
            track_url = track['url']
            par_list.append([track_name, track_url,
                             event, client, counter, msg.id, length])

        up_cc = 0
        files = []
        futures = [self.get_file(self.create_session(), *args) for args in par_list]
        if arg == 'zip':
            files = await asyncio.gather(*futures)
        else:
            for future in asyncio.as_completed(futures):
                file = await future
                await client.edit_message(event.message.to_id, msg.id,
                                          f'Uploading... {up_cc}/{len(par_list)}')
                await event.reply(file=file)
                files.append(file)
                up_cc += 1

        if arg and arg == 'zip':
            zipf = zipfile.ZipFile(join(randname, f'{owner}_{post_id}.zip'), 'w')
            for _file in files:
                zipf.write(_file, compress_type=zipfile.ZIP_DEFLATED)
            zipf.close()

            await client.edit_message(event.message.to_id, msg.id,
                                      'Uploading...')
            await event.reply(file=join(randname, f'{owner}_{post_id}.zip'))

            os.remove(join(randname, f'{owner}_{post_id}.zip'))

        if self.config.DELETE_AFTER_UPLOAD:
            for file in files:
                os.remove(file)
            os.rmdir(randname)
        await client.delete_messages(event.message.to_id, msg.id)


    async def call_executor(self, event, client):
        check = event.raw_text.split(' ')
        if len(check) < 2:
            return

        arg = None
        for item in check:
            if item != 'zip' and len(item) > 4:
                url = item
            else:
                arg = item

        post_id = None
        link = -1

        # extract wall post / playlist ID
        wall_url = '/wall'
        link = url.find(wall_url)
        if link != -1:
            self.debug('VK Wall')
            post_id = url[link+len(wall_url):]

            check = post_id.find('?')
            if check != -1:
                post_id = post_id[:check]
        else:
            self.debug('Playlist')
            convert = 'music/playlist/'
            if convert in url:
                pl_pos = url.find(convert)
                url = 'https://m.vk.com/audio?act=audio_playlist' + url[pl_pos+len(convert):]
            playlist_url = 'audio_playlist'
            link = url.find(playlist_url)
            if link != -1:
                post_id = url
            else:
                playlist_url = 'music/album'
                link = url.find(playlist_url)
                if link != -1:
                    post_id = url
        if link != -1:
            try:
                await self.post_dl(event, client, post_id, arg)
            except JSONDecodeError:
                print(traceback.print_exc())
                await event.reply(('Error: Could not load the playlist.'))
            except ValueError:
                print(traceback.print_exc())
                await event.reply(('Error: Could not find '
                                   'root element for audio files.'))
            return

        usr_url = '/audios'
        link = url.find(usr_url)
        if link != -1:
            self.debug('VK Audio')
            user_id = url[link+len(usr_url):]

            await self.user_dl(event, client, user_id, arg)
