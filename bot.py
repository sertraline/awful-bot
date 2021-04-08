#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from telethon import TelegramClient, events
from telethon import utils

import traceback
import os, sys

from core import logger
from core import media
from core import actions
from core.sqlite import SqliteInterface
from core.controller import CommandController

from core.events.edited import EditObserver
from core.events.new import NewMessageObserver
from core.events.chat_action import ChatActionObserver

import config


def main():
    actions.check_directories(config)

    mimes = ['image/png', 'image/jpeg', 'image/bmp', 'image/gif',
            'image/webp', 'video/mp4', 'video/quicktime',
            'audio/mp3', 'audio/ogg', 'audio/m4a', 'audio/flac',
            'audio/aac', 'image', 'document', 'text', 'audio']

    _debug_instance = logger.DebugLogging(config.DEBUG)
    debug_logger = _debug_instance.logger.debug

    sqlite = SqliteInterface(debug_logger)

    media_proc = media.MediaProcessor(config, debug_logger, sqlite, mimes)
    controller = CommandController(config, sqlite, debug_logger)
    archiver = logger.Archiver(debug_logger)

    edit_observer = EditObserver(mimes, utils, logger, debug_logger, sqlite, actions)
    new_message_observer = NewMessageObserver(config, controller, actions,
                                              archiver, media_proc, utils,
                                              logger, mimes, debug_logger, sqlite)
    chat_action_observer = ChatActionObserver(logger, utils)

    if config.PROXY_HOST and config.PROXY_PORT:
        import socks
        proxy = (socks.SOCKS5, config.PROXY_HOST, config.PROXY_PORT)
        debug_logger(f"Logging in using {config.PROXY_HOST}:{config.PROXY_PORT} as proxy.")
    else:
        proxy = None

    try:
        with TelegramClient('session', config.API_ID, config.API_HASH, proxy=proxy) as client:
            client.add_event_handler(edit_observer.message_edited)
            client.add_event_handler(new_message_observer.new_message)
            client.add_event_handler(chat_action_observer.chat_action)
            debug_logger("Client init")
            client.start()
            client.run_until_disconnected()
    except Exception:
        debug_logger(str(traceback.print_exc()))


if __name__ in '__main__':
    main()