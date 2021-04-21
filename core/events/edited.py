from datetime import datetime
from telethon import events


class EditObserver:

    def __init__(self, mimes, utils, logger, debug, sqlite, actions):
        self.mimes = mimes
        self.utils = utils
        self.logger = logger
        self.debug = debug
        self.actions = actions
        self.sqlite = sqlite

    @events.register(events.MessageEdited)
    async def message_edited(self, event):
        """ Catch "message edit" events. """
        from_id = self.actions.get_entity_id(event.message)
        check = self.actions.check_lists(self.sqlite, from_id)
        if not check:
            self.debug("User blacklisted: %d" % from_id)
            return

        entity = await self.actions.get_entity(event, event.client)

        dts = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        reply_msg_id = event.message.id
        if event.message.media is None:
            messg = event.raw_text
        else:
            for mime in self.mimes:
                if mime in event.message.file.mime_type:
                    size = int(event.message.file.size/1024)
                    messg = f"[%s %02d KB] " % (mime, size) + event.raw_text
                    break
        if event.message.file:
            if event.message.file.ext == '.oga':
                messg = "[voice] " + event.raw_text

        chat_name = self.utils.get_display_name(await event.client.get_entity(event.to_id))
        user_name = self.utils.get_display_name(entity)
        try:
            self.logger.msg_log_edit(dts, chat_name,
                                     str(reply_msg_id),
                                     user_name, from_id,
                                     messg)
        except Exception as e:
            print(e)
