from datetime import datetime
from telethon import events
import traceback
import os


class NewMessageObserver:

    def __init__(self, config, controller, actions, archiver,
                 media_proc, utils, logger, mimes, debug, sqlite):
        self.config = config
        self.controller = controller
        self.actions = actions
        self.archiver = archiver
        self.media_proc = media_proc
        self.utils = utils
        self.logger = logger
        self.mimes = mimes
        self.debug = debug
        self.sqlite = sqlite

    @events.register(events.NewMessage)
    async def new_message(self, event=None):
        try:
            from_id = self.actions.get_entity_id(event.message)
            to_id = await event.client.get_entity(event.to_id)

            check = self.actions.check_lists(self.sqlite, from_id, to_id.id)
            if not check:
                self.debug("User or chat blacklisted: %s, %s" % (from_id, to_id))
                return

            entity = await self.actions.get_entity(event, event.client)
            user_name = self.utils.get_display_name(entity)

            dts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            dts_fname = datetime.now().strftime("%Y%m%d_%H%M%S")

            self.archiver.check()

            # if message in msg_tracker, forward to yourself
            forwarded = False
            check = self.sqlite.check_lists_queue('msg_tracker', from_id)
            if check:
                await event.client.forward_messages('me', event.message,
                                                    event.message.to_id)
                # mark the message as already forwarded
                forwarded = True

            if event.message.media is None:
                messg = event.raw_text
            else:
                messg = await self.media_proc.process_media(os.getcwd(), event,
                                                            event.client, dts_fname,
                                                            forwarded)
            if not event.message.reply_to:
                chat_name = self.utils.get_display_name(
                    await event.client.get_entity(event.to_id)
                )
                self.logger.new_msg_log(dts, event.message.id, chat_name,
                                        user_name, from_id, messg)
            else:
                reply_to_usr = "-"
                reply_to_usr_id = "-"
                reply_msg_id = event.message.reply_to.reply_to_msg_id
                reply_to_usr_text = "-"
                async for msg in event.client.iter_messages(event.to_id,
                                                            max_id=reply_msg_id+1,
                                                            min_id=reply_msg_id-1):
                    if msg.id == reply_msg_id:
                        reply_to_usr_id = self.actions.get_entity_id(msg)
                        reply_to_usr = self.utils.get_display_name(
                                            await event.client.get_entity(reply_to_usr_id)
                                        )
                        if not msg.media:
                            reply_to_usr_text = msg.text
                        else:
                            for mime in self.mimes:
                                if mime in msg.file.mime_type:
                                    reply_to_usr_text = "[%s] " % mime + msg.text
                                    break
                            if hasattr(msg.file, 'ext'):
                                if msg.file.ext == '.oga':
                                    reply_to_usr_text = "[voice]"
                                if msg.file.sticker_set:
                                    reply_to_usr_text = "[sticker]"
                        break
                if reply_to_usr_text:
                    reply_to_usr_text = reply_to_usr_text if len(
                                            reply_to_usr_text
                                        ) <= 50 else reply_to_usr_text[:50] + '...'

                    chat_name = self.utils.get_display_name(
                        await event.client.get_entity(event.to_id)
                    )
                    self.logger.msg_reply_log(dts, event.message.id, chat_name,
                                              user_name, from_id, reply_to_usr,
                                              reply_to_usr_id, reply_msg_id,
                                              reply_to_usr_text, messg)
        except Exception:
            self.debug(traceback.print_exc())
        try:
            # save user and user id in the database
            self.sqlite.insert_call_stack(int(from_id), user_name)
            await self.controller.distribute(event, event.client)
        except Exception:
            self.debug(traceback.print_exc())
