import requests
import os


def check_directories(config):
    if not os.path.isdir("logs"):
        os.mkdir("logs")
    if not os.path.isdir('voices'):
        os.mkdir('voices')
    if not os.path.isdir('images'):
        os.mkdir('images')


def check_lists(sqlite, user_id, chat_id=None):
    check_whitelist = sqlite.check_whitelist()
    
    if check_whitelist:

        check = sqlite.check_lists_queue('whitelist', user_id)
        if check:
            # if whitelist and user_id in whitelist
            return True

        if chat_id:
            check = sqlite.check_lists_queue('whitelist', chat_id)
            if not check:
                sqlite.check_lists_queue('whitelist', int(f"100{chat_id}"))
            if check:
                return True

        return False

    if chat_id:
        check = sqlite.check_lists_queue('blacklist', chat_id)
        if not check:
            check = sqlite.check_lists_queue('blacklist', int(f"100{chat_id}"))

        if check:
            # if blacklist and the whole chat in blacklist
            return False

    check = sqlite.check_lists_queue('blacklist', user_id)
    if check:
        # if blacklist and user_id in blacklist
        return False
    # if not whitelist and not blacklist
    return True


async def get_my_id(client):
    _id = await client.get_entity('me')
    return _id.id


async def get_entity(event, client, spec_id=None):
    if not spec_id:
        from_id = event.message.from_id
        if from_id:
            from_id = from_id.user_id
        else:
            from_id = event.message.peer_id
            if hasattr(from_id, 'user_id'):
                from_id = from_id.user_id
            else:
                from_id = from_id.channel_id
    else:
        from_id = spec_id

    entity = None

    try:
        entity = await client.get_entity(from_id)
    except Exception:
        await client.get_dialogs()

        sets = await event.get_input_chat()

        if hasattr(sets, 'channel_id'):
            cid = sets.channel_id
            await client.get_participants(cid)

        entity = await client.get_entity(from_id)

    return entity


def find_user_by_username(name: str, sqlite) -> int:
    out = sqlite.fetch_call_stack()

    for row in out:
        user_id = row[1]
        username = row[2]

        if name == username:
            return user_id
    return None


async def get_entity_by_any(event, client, entity_id, sqlite):
    spec_id = entity_id.strip('-')
    if spec_id.isdigit():
        spec_id = int(spec_id)

    try:
        entity = await get_entity(event, client, spec_id)
        return entity
    except ValueError:
        user_id = find_user_by_username(spec_id, sqlite)
        if user_id:
            try:
                entity = await get_entity(event, client, user_id)
                await event.reply('```'+str(entity)+'```')
                return entity
            except:
                pass
    return None


def get_entity_id(message):
    from_id = message.from_id
    if from_id:
        from_id = from_id.user_id
    else:
        from_id = message.peer_id
        if hasattr(from_id, 'user_id'):
            from_id = from_id.user_id
        else:
            from_id = from_id.channel_id
    return from_id


def get_log_path():
    files = os.listdir('logs')

    latest = 0
    file = None
    for _f in files:
        if _f.endswith('zip'):
            continue
        _stat = os.path.getmtime(os.path.join('logs', _f))
        if _stat > latest:
            latest = _stat
            file = _f

    return os.path.join('logs', file)


def safe_request(url, data=None, proxy=None, ssl=True):
    if proxy:
        proxy = {
            'http': 'socks5://127.0.0.1:9050',
            'https': 'socks5://127.0.0.1:9050'
        }
    headers = {
        'User-Agent': ('Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 '
                       '(KHTML, like Gecko) Chrome/84.0.4147.105 Safari/537.36')
    }
    if not data:
        r = requests.get(url, headers=headers,
                         proxies=proxy,
                         verify=ssl)
    else:
        r = requests.post(url, headers=headers,
                          data=data,
                          proxies=proxy,
                          verify=ssl)
    return r
