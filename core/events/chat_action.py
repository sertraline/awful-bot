from telethon import events
from telethon.tl.functions.users import GetFullUserRequest

class ChatActionObserver():

    def __init__(self, logger, utils):
        self.logger = logger
        self.utils = utils


    @events.register(events.ChatAction)
    async def chat_action(self, event):
        """ Catch user join/left events. """
        if event.user_joined or event.user_left:
            try:
                usr = event.users[0]
            except IndexError:
                return
            usr = await event.client(GetFullUserRequest(usr))
            await self.logger.msg_log_chat_action(usr, event, event.client, self.utils)