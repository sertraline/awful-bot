from telethon.tl.types import PeerUser, User, Channel, Chat
from .private import PrivateExecutor
from .media import MediaExtractor
from .logger import DebugLogging
from .actions import get_my_id, get_entity_by_any
from datetime import datetime, timedelta
from . import modules
import traceback
import inspect
import pkgutil
import re

class ObjectHarvester():

    def __init__(self, debug):
        self.debug = debug


    def harvest(self, ignore_list : list, args : list):
        """
        Dynamically import modules ignoring disabled modules in the config.
        """
        objects = []
        for _loader, _module_name, _ in  pkgutil.walk_packages(modules.__path__):
            if _module_name in ignore_list:
                continue
            _module = _loader.find_module(_module_name).load_module(_module_name)
            # Assign module to the global scope
            globals()[_module_name] = _module

            # Find out arguments accepted by the executor
            func_args = inspect.getfullargspec(_module.Executor)

            local_args = args[:]
            if len(func_args.args) == 3:
                local_args = [args[0], args[1]]

            obj = _module.Executor(*local_args)
            self.debug(f"INIT {obj}")
            objects.append(obj)
        return objects


class CommandController():

    commands = {}
    global_help = ''

    out_end_isnext = '\n\n[get] [next]```'
    out_end_nonext = '\n\n[get]```'

    DELAY = [None, None]

    def __init__(self, config, sqlite, debug):
        self.id = None
        self.config = config
        self.sqlite = sqlite
        self.debug = debug
        self.extractor = MediaExtractor()
        self.private = PrivateExecutor(self.config, self.debug, self.sqlite)
        self.call_harvester()
        self.map_objects()


    def call_harvester(self):
        self.harvester = ObjectHarvester(self.debug)
        self.objects = self.harvester.harvest(self.config.IGNORE,
                                              [self.config, self.debug, self.extractor])


    async def help(self, event):
        TDELTA, TDELTA_ID = self.DELAY
        if TDELTA and TDELTA_ID:
            if datetime.now() < TDELTA and TDELTA_ID == event.message.to_id:
                self.debug("Skipping the message due to delay")
                return
        self.DELAY[0] = datetime.now() + timedelta(seconds=30)
        self.DELAY[1] = event.message.to_id

        await event.reply(self.global_help)


    def map_objects(self):
        """
        Map each object to its own command and executor.
        Prepend _cmd_start (any symbol defined in config, '!', '/', in other words
                            the start of the command).
        Append _cmd_end (defined in config) to represent a full command
        (!command@call_name) if use_call_name is defined in the object.
        """
        self.commands = {}

        _cmd_start = self.config.S
        _cmd_end = self.config.CALL_NAME

        for obj in self.objects:
            obj.command = _cmd_start + obj.command
            obj.command = obj.command + _cmd_end if obj.use_call_name else obj.command

            argspec = inspect.getfullargspec(obj.call_executor)

            self.commands[obj.command] = {
                'executor': obj.call_executor,
                'args': {arg:None for arg in argspec.args if arg != 'self'},
            }

            try:
                if obj.placeholders:
                    self.commands[obj.command]['placeholders'] = obj.placeholders
            except AttributeError:
                pass

            self.global_help += obj.help()
            self.global_help += '\n\n'
        
        self.global_help = '```' + self.global_help + '```'

        self.commands.update(self.private.command_controller)

        self.commands[_cmd_start+'help'+_cmd_end] = {
            'executor': self.help, 'args': {'event': None}
        }

        # reserved commands to pull out data from sqlite
        self.reserved = ['next', 'get', 'cancel']


    async def distribute(self, event, client):
        if not self.id:
            self.id = await get_my_id(client)
        
        # check for interaction with queues
        if any([event.raw_text.startswith(key) for key in self.reserved]):
            _out = await self.check_queues(event, client)
            if _out:
                return

        for key, val in self.commands.items():

            test = event.raw_text.split(' ')[0]

            if 'placeholders' in val:
                if not any([key+x == test for x in val['placeholders']]):
                    continue
            else:
                if not key in test:
                    continue
            
            # check if private method is called
            if key in self.private.command_controller.keys():
                if type(event.message.to_id) is PeerUser:
                    if int(event.message.to_id.user_id) != int(self.id):
                        self.debug(('Ignoring attempt of private '
                                   f'method call: {event.to_id.user_id} != {self.id}'))
                        return

            self.debug(f'Call: {event.raw_text}')

            local = {key:None for key in val['args'].keys()}

            # map arguments
            for arg in [['event', event], ['client', client], ['key', key]]:
                if arg[0] in local.keys():
                    local[arg[0]] = arg[1]
            try:
                await val['executor'](**local)
            except Exception:
                self.debug(str(traceback.print_exc()))
            break


    async def check_queues(self, event, client):
        # check for existing queue from this user id in the table

        user = await client.get_entity(event.message.to_id)
        to_id = user.id
        from_id = event.message.from_id
        to_msg_id = event.message.reply_to_msg_id

        if event.raw_text.strip() == 'cancel':
            check = self.sqlite.check_current_queue(user_id=from_id, chat_id=to_id)
            if not check:
                return
            
            self.sqlite.clear_user_queue(user_id=from_id, chat_id=to_id)
        elif event.raw_text.strip() == 'next':
            # pop next item from the queue (if queue from this id exists)
            check = self.sqlite.check_future_queue(user_id=from_id, chat_id=to_id)

            if check:
                self.debug("[next] Fetching next item from queue")
                query, root_id = self.sqlite.fetch_next_from_queue(user_id=from_id,
                                                                   chat_id=to_id)
                
                check = self.sqlite.check_future_queue(user_id=from_id, chat_id=to_id)
                if check:
                    query = '```' + query + self.out_end_isnext
                else:
                    query = '```' + query + self.out_end_nonext

                self.debug(query)
                msg = await event.reply(query)

                self.sqlite.add_childs_current_queue(msg.id, root_id)
                return True

        elif event.raw_text.startswith('get '):
            # get selector from the message
            command = event.raw_text.split(' ')

            try:
                _choice = int(command[1])
            except ValueError:
                return

            if to_msg_id:
                check = self.sqlite.check_current_queue(user_id=from_id, 
                                                        chat_id=to_id,
                                                        msg_id=to_msg_id)
                if not check:
                    return
                self.debug("[get] Fetching current_queue [reply]")
                query = self.sqlite.fetch_current_queue(user_id=from_id,
                                                        chat_id=to_id,
                                                        msg_id=to_msg_id)
            else:
                kw = 'item_action_selected'
                check = self.sqlite.check_current_queue(user_id=from_id,
                                                        chat_id=to_id,
                                                        keywords=kw)
                if not check:
                    kw = 'display_items_table'
                    check = self.sqlite.check_current_queue(user_id=from_id,
                                                            chat_id=to_id,
                                                            keywords=kw)
                    if not check:
                        return

                self.debug("[get] Fetching current_queue")
                query = self.sqlite.fetch_current_queue(user_id=from_id,
                                                        chat_id=to_id,
                                                        keywords=kw)

            self.debug(f"Query: {query}")

            sqlite_key = query[0][3]
            keyword = query[0][4]
            query_selection = query[0][5]

            query = query[0][2].split('\n')

            command_key = None
            for key, val in self.commands.items():
                if key == sqlite_key and 'actions' in val:
                    command_key = key
                    break

            self.debug(f"[get] Checking for action display: {keyword}")
            if keyword == 'display_items_table':
                # 'get' for display_items_table -> request to display actions for item
                for item in query:
                    item = re.sub(r'[\[\]]', '', item)
                    item = re.sub(r' +', ' ', item)

                    _item_id, *_ = item.split(' ')
                    if int(command[1]) == int(_item_id):
                        self.debug("[get] "
                                  f"[{command_key}] Display actions "
                                  f"for selected item: <{item}>")

                        await self.display_actions(event, client, command_key, item)
                        return True
            elif keyword == 'item_action_selected':
                # item from displayed actions was selected
                selection_key = None
                for item in query:
                    # clear the message
                    item = re.sub(r'[\[\]]', '', item)
                    item = re.sub(r' +', ' ', item)

                    _item_id, *rest = item.split(' ')
                    self.debug(rest)
                    
                    # if user choice corresponds to row in the message
                    if int(command[1]) == int(_item_id):
                        rest = [x for x in rest if not 'add' in x and not 'remove' in x]
                        rest = ' '.join(rest)
                        selection_key = rest.strip()
                        break
                if selection_key:
                    self.debug(f"[get] Requested selection key: {selection_key}")
                    for key in self.commands[command_key]['actions'].keys():
                        if rest.strip() == key:
                            method = self.commands[command_key]['actions'][key]

                            self.debug(f"[get] Requested method call: {method}")

                            await method(event, client, query_selection)
                            return True


    async def display_actions(self, event, client, key, item):
        # clear the message
        item = re.sub(r'[\[\]]', '', item)
        item = re.sub(r' +', ' ', item)

        _, entity_id, *_ = item.split(' ')
        from_id = event.message.from_id
        chat_id = event.message.to_id.user_id

        #entity = await get_entity_by_any(event, client, entity_id, self.sqlite)
        #if type(entity) is User:

        _action_list = []
        for kkey, vval in self.commands.items():
            if key == kkey:
                if vval['prepare']:
                    prepared = await vval['prepare'](self, entity_id,
                                                     vval['actions'],
                                                     event,
                                                     client)
                    for k in prepared.keys():
                        _action_list.append(k)
                else:
                    for k in vval['actions'].keys():
                        _action_list.append(k)

        _output_string = [f'[{cc}] {x}' for cc, x in enumerate(_action_list, start=1)]

        _fmt_output_string = '```' + '\n'.join(_output_string) + '```'
        msg = await event.reply(_fmt_output_string)

        self.sqlite.insert_current_queue(user_id=from_id,
                                         user_data='\n'.join(_output_string),
                                         method=key,
                                         keywords='item_action_selected',
                                         msg_id=msg.id,
                                         selection=entity_id,
                                         chat_id=chat_id)
