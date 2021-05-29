from telethon.tl.types import InputStickerSetID, InputStickerSetEmpty
from telethon.tl.functions.messages import GetStickerSetRequest
from PIL import Image
import pysftp
import os
import traceback
from . import actions


class MediaProcessor:

    def __init__(self, config, debug, sqlite, mimes):
        self.config = config
        self.debug = debug
        self.sqlite = sqlite
        self.mimes = mimes

    async def process_media(self, dirname: str, event,
                            client, dts: str, forwarded: bool) -> str:
        """
        Check message for media, detect mimetype and filesize.
        Get stickerpack name if message is sticker.
        Download media if downloads are enabled.
        """
        if not hasattr(event.message.file, 'ext'):
            return event.raw_text

        from_id = actions.get_entity_id(event.message)
        to_id_key = next(iter(event.message.to_id.__dict__.keys()))
        to_id = event.message.to_id.__dict__[to_id_key]

        # if voice
        if event.message.file.ext == '.oga':
            ext = event.message.file.ext
            messg = "[voice %d sec.]" % event.message.file.duration

            check = self.sqlite.check_lists_queue('voice_tracker', from_id)
            if not check:
                check = self.sqlite.check_lists_queue('voice_tracker', to_id)
                if not check:
                    check = self.sqlite.check_lists_queue('voice_tracker',
                                                          int('100%s' % to_id))
                    if not check:
                        return messg

            fname = os.path.join(dirname, "voices", "%s_%s" % (from_id, dts))
            await client.download_media(event.message, file=fname)
            await client.send_message('me', '#media %s in %s' % (from_id, to_id))
            if not forwarded:
                await client.forward_messages('me', event.message,
                                              event.message.to_id)
            self.debug("Saved voice file: %s" % fname)

            if self.config.SFTP_ENABLED:
                try:
                    self.send_sftp('%s %s%s' % (from_id, dts, ext), 'voices')
                except Exception:
                    traceback.print_exc()
            return messg

        # if sticker
        if event.message.file.sticker_set and \
                type(event.message.file.sticker_set) is not InputStickerSetEmpty:
            stick = event.message.file.sticker_set
            stickers = await client(GetStickerSetRequest(
                            stickerset=InputStickerSetID(
                                id=stick.id,
                                access_hash=stick.access_hash
                            )
                        ))
            messg = "[sticker (%s)]" % stickers.set.title
            return messg

        mime = None
        for mtype in self.mimes:
            if mtype in event.message.file.mime_type:
                mime = mtype
                break
        if mime:
            size = int(event.message.file.size/1024)
            messg = f"[%s %02d KB] " % (mime, size) + event.raw_text

            check = self.sqlite.check_lists_queue('image_tracker', from_id)
            if not check:
                check = self.sqlite.check_lists_queue('image_tracker', to_id)
                if not check:
                    try:
                        check = self.sqlite.check_lists_queue('image_tracker',
                                                              int('100%s' % to_id))
                    except Exception as e:
                        print(e)
                    if not check:
                        return messg

            if 'image' in mime:
                if 'webp' in event.message.file.mime_type \
                        and not type(event.message.file.sticker_set) is InputStickerSetEmpty:
                    return messg
                ext = event.message.file.ext
                if ext == '.jpe':
                    ext = '.jpeg'

                fname = os.path.join("images", "%s_%s%s" % (from_id, dts, ext))
                await client.download_media(event.message, file=fname)
                await client.send_message('me', '#media %s in %s' % (from_id, to_id))
                if not forwarded:
                    await client.forward_messages('me',
                                                  event.message,
                                                  event.message.to_id)
                self.debug("Image saved: %s" % fname)

                if 'png' in event.message.file.mime_type and self.config.OPT_PNG:
                    opt = Image.open(fname)
                    self.debug("Image loaded: %s" % fname)

                    opt.save(fname, 'PNG', quality=70)
                    self.debug("Reduced quality of PNG file: %s" % fname)

                if 'webp' in event.message.file.mime_type and self.config.CONV:
                    conv = Image.open(fname)
                    self.debug("Image loaded: %s" % fname)

                    conv.save(fname.replace('.webp', '.png'), format='PNG')
                    os.remove(fname)

                    fname = fname.replace('.webp', '.png')
                    print("Converted .webp to .png: %s" % fname)

                if self.config.SFTP_ENABLED:
                    try:
                        self.send_sftp(fname, 'images')
                    except Exception:
                        traceback.print_exc()
            return messg

    def send_sftp(self, source_file: str, dest_dir: str):
        self.debug("Connecting to SFTP")

        with pysftp.Connection(host=self.config.SFTP_HOST,
                               username=self.config.SFTP_USR,
                               private_key=self.config.SFTP_KEY,
                               port=int(self.config.SFTP_PORT),
                               log=True) as sftp:
            upload_dir = self.config.SFTP_DIR

            if not sftp.isdir(upload_dir+'/'+dest_dir):
                sftp.mkdir(upload_dir+'/'+dest_dir)
                self.debug('mkdir %s/%s' % (upload_dir, dest_dir))

            sftp.put(dest_dir+'/'+source_file, upload_dir+'/'+dest_dir+'/'+source_file)
            self.debug("PUT: %s/%s/%s" % (upload_dir, dest_dir, source_file))

        self.debug("Connection closed.")


class MediaExtractor:

    def __init__(self):
        pass

    async def download_media(self, event, client, fname: str) -> str:
        """
        Download image attached to message and return its filepath.
        If media is not available, look up for image attached to message
        user replied to.
        """
        if event.message.media:
            mime = event.message.file.mime_type
            if 'image' in mime or 'video' in mime or 'audio' in mime:
                ext = event.message.file.ext
                if ext == '.jpe':
                    ext = '.jpg'
                fname += ext
                await client.download_media(event.message, file=fname)
                return fname

        reply_msg_id = event.message.reply_to_msg_id
        if not reply_msg_id:
            return None

        async for msg in client.iter_messages(
                event.to_id, max_id=reply_msg_id+1, min_id=reply_msg_id-1
        ):
            if msg.id == reply_msg_id:
                if msg.media:
                    mime = msg.file.mime_type
                    if 'image' in mime or 'video' in mime or 'audio' in mime:
                        ext = msg.file.ext
                        if ext == '.jpe':
                            ext = '.jpg'
                        fname += ext
                        await client.download_media(msg, file=fname) 
                        return fname
                else:
                    break
        return
