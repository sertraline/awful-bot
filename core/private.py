from .actions import get_my_id, get_entity_by_any, get_entity, get_log_path, safe_request
from telethon.tl.functions.photos import UploadProfilePhotoRequest
from telethon.tl.functions.contacts import ResolveUsernameRequest
from telethon.tl.functions.channels import GetFullChannelRequest
from telethon.tl.functions.messages import GetFullChatRequest
from telethon.tl.functions.users import GetFullUserRequest
from telethon.tl.types import PeerUser, User, Channel, Chat
from telethon.errors.rpcerrorlist import ChatAdminRequiredError
from os import remove

class PrivateExecutor():

    command_controller = {}
    out_end_isnext = '\n\n[get] [next]'
    out_end_nonext = '\n\n[get]'

    def __init__(self, config, debug, sqlite):
        self.config = config
        self.debug = debug
        self.sqlite = sqlite
        self.id = None

        _cmd_start = self.config.S

        _user_actions = {
            'Get entity info': self.get_user_info,
            'Blacklist': self.blacklist,
            'Whitelist': self.whitelist,
            'Track voices': self.voice_tracker,
            'Track images': self.image_tracker,
            'Track all messages': self.msg_tracker
        }

        # command_controller: is merged with public controller,
        # but only executes when the command is coming from
        # the owner of client (self id)

        self.command_controller = {
            _cmd_start+'private': {
                'executor': self.help,
                'args': {'client': None}
            },
            _cmd_start+'remove': {
                'executor': self.remove_msg,
                'args': {'event': None, 'client': None}
            },
            _cmd_start+'anon': {
                'executor': self.become_leet_hacker,
                'args': {'event': None, 'client': None}
            },
            _cmd_start+'dialogs': {
                'executor': self.get_user_dialogs,
                'args': {'event': None, 'client': None, 'key': None},
                'actions': _user_actions,
                'prepare': self.prepare_user_actions
            },
            _cmd_start+'info': {
                'executor': self.get_user_info,
                'args': {'event': None, 'client': None}
            },
            _cmd_start+'ids': {
                'executor': self.get_last_ids,
                'args': {'event': None, 'key': None},
                'actions': _user_actions,
                'prepare': self.prepare_user_actions
            },
            _cmd_start+'manage': {
                'executor': self.manage_lists,
                'args': {'event': None, 'client': None, 'key': None},
                'actions': _user_actions,
                'prepare': self.prepare_user_actions
            },
            _cmd_start+'blacklist': {
                'executor': self.blacklist,
                'args': {'event': None, 'client': None}
            },
            _cmd_start+'whitelist': {
                'executor': self.whitelist,
                'args': {'event': None, 'client': None}
            },
            _cmd_start+'track_voice': {
                'executor': self.voice_tracker,
                'args': {'event': None, 'client': None}
            },
            _cmd_start+'track_images': {
                'executor': self.image_tracker,
                'args': {'event': None, 'client': None}
            },
            _cmd_start+'track_messages': {
                'executor': self.msg_tracker,
                'args': {'event': None, 'client': None}
            },
            _cmd_start+'log': {
                'executor': self.get_log,
                'args': {'client': None}
            },
            _cmd_start+'last': {
                'executor': self.display_log,
                'args': {'event': None, 'client': None}
            }
        }

        # 'actions': define if command interacts with sqlite interface
        # 'prepare': define a method to prepare output before giving it to sqlite interface


    async def help(self, client):
        S = self.config.S
        st = (
            f"{S}private: display this help\n\n"
            f"{S}manage [list]\n"
            f"Manage SQL list. Send {S}manage without "
            "arguments to get a list of SQL lists.\n\n"
            f"{S}remove: [count] [chat username or ID]\n"
            f"Remove messages from chat: '{S}remove 10 chatname'\n\n"
            f"{S}dialogs: get list of open dialogs.\n"
            f"{S}ids: get list of IDs encountered by bot.\n"
            f"{S}info [username]: display user info.\n"
            f"{S}blacklist [user_id]: ignore requests from user_id.\n\n"
            f"{S}whitelist [user_id]: users NOT in whitelist "
            "will be ignored. If you add another chat or user "
            "to whitelist, you will be added automatically.\n\n"
            f"{S}track_voice [user_id]\n"
            f"{S}track_images [user_id]\n"
            f"{S}track_messages [user_id]\n"
            f"{S}log: get current log\n"
            f"{S}last [N]: display last N events from bot log [default: 8]"
        )
        await client.send_message('me', '```'+st+'```')


    async def remove_msg(self, event, client):
        """
        Remove message from the chat.
        Is called manually in format: command message_count
        """ 
        if not self.id:
            self.id = await get_my_id(client)
            self.debug(f"Retrieved self ID: {self.id}")

        groups = event.raw_text
        groups = groups.split()
        if int(groups[1]) > 15000:
            await event.reply(("Abort.\nUsage:\n/remove [limit] [id1] "
                               "[id2] [idN]\nLimit cannot be >15000."))
        else:
            lim = groups[1]
            for group in groups[2:]:
                if group.strip('-').isdigit():
                    group = int(group)

                plh = f"Started cleanup: {group}, {lim}"
                status_msg = await client.send_message("me", plh)
                await client.get_entity(group)

                messages = await client.get_messages(group, limit=int(lim),
                                                     from_user=int(self.id))

                for message in messages:
                    await message.delete()
                    self.debug(f"Removed: {message.date}, {message.text}")

                await client.edit_message(event.message.to_id, status_msg.id,
                                          f'Removed {lim} messages from {group}.')


    async def get_user_dialogs(self, event, client, key):
        """
        Get list of open dialogs in the user client, process, and
        if length is bigger than 45 items, prepare interactive interface
        for fetching next items.
        """
        dialogs = await client.get_dialogs()
        from_id = event.message.from_id

        self.sqlite.clear_user_queue(from_id, event.message.to_id.user_id)

        result = [f'[{cc}] [{dialog.id:<16}] {dialog.name[:35]}' \
                    for cc, dialog in enumerate(dialogs, start=1)]

        if len(result) <= 45:
            result = '\n'.join(result)
            fmt_result = '```' + result + self.out_end_nonext + '```'
            msg = await event.reply(fmt_result)

            self.debug("Insert output in current_queue")
            self.sqlite.insert_current_queue(from_id, result,
                                             key, 'display_items_table',
                                             msg.id)
        else:
            full_queue = '\n'.join(result)
            chunks = [result[i:i+45] for i in range(0, len(result), 45)]

            result = '\n'.join(chunks[0])
            result = '```' + result + self.out_end_isnext + '```'
            msg = await event.reply(result)

            self.debug("Insert output [chunks] in current_queue")
            self.sqlite.insert_current_queue(from_id, full_queue,
                                             key, 'display_items_table',
                                             msg.id)

            chunks = chunks[1:]
            self.debug("Insert [chunks] in future_queue")
            for chunk in chunks:
                self.sqlite.insert_future_queue(from_id, '\n'.join(chunk),
                                                key, 'next', msg.id)
    

    async def get_last_ids(self, event, key):
        """
        Get entity IDs from the database, process, and
        if length of list is bigger than 45 items, prepare interactive interface
        for fetching next items.
        """
        self.debug("Retrieve list of IDs from the call_stack")
        from_id = event.message.from_id
        self.sqlite.clear_user_queue(from_id, event.message.to_id.user_id)

        out = self.sqlite.fetch_call_stack()

        user_list = []
        for row in out:
            user_id = row[0]
            username = row[1]

            if len(username) > 35:
                username = username[:35]+'...'

            user_list.append([user_id, username])

        user_list = [f'[{cc:<2}] [{x[0]:<12}] {x[1]}' \
                        for cc, x in enumerate(user_list, start=1)]

        if len(user_list) <= 45:
            user_list = '\n'.join(user_list)
            fmt_user_list = '```' + user_list + self.out_end_nonext + '```'
            msg = await event.reply(fmt_user_list)

            self.debug("Insert output in current_queue")
            self.sqlite.insert_current_queue(from_id, user_list,
                                             key, 'display_items_table',
                                             msg.id)
        else:
            full_queue = '\n'.join(user_list)
            chunks = [user_list[i:i+45] for i in range(0, len(user_list), 45)]

            user_list = '\n'.join(chunks[0])
            user_list = '```' + user_list + self.out_end_isnext + '```'
            msg = await event.reply(user_list)

            self.debug("Insert output [chunks] in current_queue")
            self.sqlite.insert_current_queue(from_id, full_queue,
                                             key, 'display_items_table',
                                             msg.id)

            chunks = chunks[1:]
            self.debug("Insert [chunks] in future_queue")
            for chunk in chunks:
                self.sqlite.insert_future_queue(from_id, '\n'.join(chunk),
                                                key, 'next', msg.id)


    async def get_user_info(self, event, client, spec_id=None):
        """
        Get full user info.
        Can be used within interactive interface, or be called manually.
        Nickname, ID or username can be used for the request,
        for instance: command username
        """
        if not spec_id:
            command = event.raw_text.split(' ')
            if len(command) < 2:
                return

            spec_id = ' '.join(command[1:])

        entity = await get_entity_by_any(event, client,
                                         spec_id, self.sqlite)
        if entity:
            await event.reply('```'+str(entity)+'```')
            return entity
        await event.reply(("Could not find an entity "
                           f"corresponding to {spec_id}."))
    

    async def prepare_user_actions(self, parent, entity_id, actions,
                                   event, client):
        """
        Process message before sending it back to the next method.
        """
        sqli = [['Blacklist', 'blacklist'], 
                ['Whitelist', 'whitelist'], 
                ['Track images', 'image_tracker'],
                ['Track voices', 'voice_tracker']]
        
        not_user = [['Track all messages', 'msg_tracker']]

        entity_type = await get_entity(event, client, int(entity_id))
        if type(entity_type) is User:
            sqli.append(not_user[0])
        else:
            entity_id = entity_id.strip('-')

        lists = {x[0]:parent.sqlite.check_lists_queue(
                            x[1], entity_id) for x in sqli}
        self.debug(lists)

        new_dict = {}
        for key, val in actions.items():
            for ck in lists.keys():
                if lists[ck] and ck == key:
                    key += ' [remove]'
                    break
                elif not lists[ck] and ck == key:
                    key += ' [add]'
                    break

            if not any([key in x[0] for x in not_user]):
                new_dict[key] = val
        
        return new_dict


    async def insert_one_column_list(self, event, client,
                                     user_id, type_list):
        if not self.id:
            self.id = await get_my_id(client)
            self.debug(f"Retrieved self ID: {self.id}")

        if not user_id:
            user_id = event.raw_text.split(' ')
            if len(user_id) == 1:
                return [-1, None]
            if not user_id[1].isdigit():
                return [-1, None]
            user_id = user_id[1]

        user_id = int(str(user_id).strip('-'))

        if type_list == 'blacklist' and int(user_id) == int(self.id):
            return [-1, 'Cannot blacklist yourself']

        if type_list == 'msg_tracker':
            entity_type = await get_entity(event, client, int(user_id))
            if type(entity_type) is not User:
                return [-1, 'Only user messages can be tracked.']

        _out = self.sqlite.insert_one_column_list(type_list, user_id)
        prepare = f"{user_id} to {type_list.replace('_', ' ')}."
        if _out:
            prepare = 'Added ' + prepare
        else:
            prepare = 'Removed ' + prepare.replace('to', 'from')
        return [0, prepare]


    async def blacklist(self, event, client, user_id=None):
        """
        Put user in blacklist.
        Requests coming from IDs in blacklist will be ignored.
        Can be used within interactive interface or be called manually,
        in format: command user_id
        """
        prepare = await self.insert_one_column_list(event, client,
                                                    user_id, 'blacklist')
        if prepare[0] == -1 and prepare[1]:
            await event.reply(prepare[1])
            return
        await event.reply(prepare[1])
    

    async def whitelist(self, event, client, user_id=None):
        """
        Put user in whitelist.
        If whitelist is present, all requests from IDs not present in
        whitelist will be ignored.
        Can be used within interactive interface or be called manually,
        in format: command user_id
        """
        prepare = await self.insert_one_column_list(event, client,
                                                    user_id, 'whitelist')
        if prepare[0] == -1 and prepare[1]:
            await event.reply(prepare[1])
            return

        is_whitelist = self.sqlite.check_whitelist()
        check = self.sqlite.check_lists_queue('whitelist', self.id)
        if is_whitelist and not check:
            # whitelist yourself in case whitelist exists
            self.sqlite.insert_one_column_list('whitelist', self.id)

        await event.reply(prepare[1])


    async def image_tracker(self, event, client, user_id=None):
        """
        Put user in image_tracker.
        Images coming from such IDs will be saved in 'images' directory.
        Can be used within interactive interface or be called manually
        in format: command user_id
        """
        prepare = await self.insert_one_column_list(event, client,
                                                    user_id, 'image_tracker')
        if prepare[0] == -1 and prepare[1]:
            await event.reply(prepare[1])
            return
        await event.reply(prepare[1])


    async def voice_tracker(self, event, client, user_id=None):
        """
        Put user in voice_tracker.
        Voices coming from such IDs will be saved in 'voices' directory.
        Can be used within interactive interface or be called manually
        in format: command user_id
        """
        prepare = await self.insert_one_column_list(event, client,
                                                    user_id, 'voice_tracker')
        if prepare[0] == -1 and prepare[1]:
            await event.reply(prepare[1])
            return
        await event.reply(prepare[1])


    async def msg_tracker(self, event, client, user_id=None):
        prepare = await self.insert_one_column_list(event, client,
                                                    user_id, 'msg_tracker')
        if prepare[0] == -1 and prepare[1]:
            await event.reply(prepare[1])
            return
        await event.reply(prepare[1])  


    async def get_log(self, client):
        import zipfile

        path = get_log_path()
        zipf = zipfile.ZipFile('log.zip', 'w')
        zipf.write(path, compress_type=zipfile.ZIP_DEFLATED)
        zipf.close()

        await client.send_file('me', 'log.zip')
        remove('log.zip')


    async def display_log(self, event, client):
        path = get_log_path()

        txt = event.raw_text.split(' ')
        count = 9
        try:
            count = int(txt[1])+1
        except:
            pass

        termcolors = ['[31m', '[32m', '[33m', '[0m']

        with open(path, 'r') as file:
            data = file.read()

        data = data.split("_"*21)
        to_filter = ('_'*21).join(data[-count:-1])
        for color in termcolors:
            to_filter = to_filter.replace(color, '')

        to_filter = to_filter.replace('`', '')

        to_filter = '```'+to_filter+'```'
        await client.send_message('me', to_filter)


    async def manage_lists(self, event, client, key):
        """
        Get list of user IDs in specified table.
        """
        from_id = event.message.from_id
        self.sqlite.clear_user_queue(from_id, event.message.to_id.user_id)

        list_types = ['whitelist', 'blacklist', 'image_tracker',
                      'voice_tracker', 'msg_tracker']

        sql_list = event.raw_text.split(' ')
        if len(sql_list) < 2:
            await event.reply('```Available lists:\n  '+ \
                              '\n  '.join(list_types)+'```')
            return
        
        sql_list = sql_list[1]
        if not sql_list in list_types:
            return

        out = self.sqlite.fetch_from_list(sql_list)

        user_list = []
        if len(out) == 0:
            await event.reply(f'{sql_list} is empty.')
            return

        for user_id in out[0]:
            out = self.sqlite.fetch_call_stack()

            username = ''
            for row in out:
                row_user_id = row[0]
                if int(row_user_id) == int(user_id):
                    username = row[1]
            user_list.append([user_id, username])   

        user_list = [f'[{cc:<2}] [{x[0]:<12}] {x[1]}' \
                        for cc, x in enumerate(user_list, start=1)]

        if len(user_list) <= 45:
            user_list = '\n'.join(user_list)
            fmt_user_list = '```' + user_list + self.out_end_nonext + '```'
            msg = await event.reply(fmt_user_list)

            self.debug("Insert output in current_queue")
            self.sqlite.insert_current_queue(from_id, user_list,
                                             key, 'display_items_table',
                                             msg.id)
        else:
            full_queue = '\n'.join(user_list)
            chunks = [user_list[i:i+45] for i in range(0, len(user_list), 45)]

            user_list = '\n'.join(chunks[0])
            user_list = '```' + user_list + self.out_end_isnext + '```'
            msg = await event.reply(user_list)

            self.debug("Insert output [chunks] in current_queue")
            self.sqlite.insert_current_queue(from_id, full_queue, key,
                                             'display_items_table', msg.id)

            chunks = chunks[1:]
            self.debug("Insert [chunks] in future_queue")
            for chunk in chunks:
                self.sqlite.insert_future_queue(from_id, '\n'.join(chunk),
                                                key, 'next', msg.id)


    async def become_leet_hacker(self, event, client):
        # Actually not safe request to thispersondoesnotexist dot com

        # IP is used directly to bypass cloudflare cancer.
        # We are not going to abuse anything so we don't need MITM inbetween.
        r = safe_request('https://95.216.76.20/image', proxy=None, ssl=False)
        with open('temp.png', 'wb') as f:
            f.write(r.content)
        await client(UploadProfilePhotoRequest(
                await client.upload_file('temp.png')
        ))
        remove('temp.png')
