from termcolor import colored
import logging
from logging.handlers import RotatingFileHandler
from os.path import join, isfile
from os import remove, listdir, stat
from datetime import datetime, timedelta
import difflib
import zipfile

class DebugLogging():

    def __init__(self, enabled):
        self.logger = logging.getLogger("awful-bot")
        _formatter = logging.Formatter(("[%(asctime)s] [%(module)11s: %(funcName)-20s()] "
                                        "%(lineno)4s    %(message)s"))
        _stream_handler = logging.StreamHandler()
        _stream_handler.setLevel(logging.DEBUG)
        _stream_handler.setFormatter(_formatter)
        _file_handler = RotatingFileHandler(filename="debug.log", 
                                            mode='a', maxBytes=10*1024*1024, 
                                            backupCount=0, encoding=None, delay=0)
        _file_handler.setFormatter(_formatter)
        self.logger.addHandler(_file_handler)
        self.logger.addHandler(_stream_handler)
        if enabled:
            self.logger.setLevel(logging.DEBUG)
        else:
            self.logger.setLevel(logging.INFO)


class Archiver():

    last_check = None

    def __init__(self, debug):
        self.debug = debug

    def check(self):
        check_date = datetime.now()
        if not self.last_check:
            self.compress_old(check_date)
        else:
            if not check_date.day > self.last_check.day:
                return
            else:
                self.compress_old(check_date)

    def compress_old(self, check_date, filepath='..'):
        day = int((check_date - timedelta(days=2)).strftime('%s'))

        for file in listdir('logs'):
            file = join('logs', file)
            if stat(file).st_mtime < day:
                self.debug(f"Compressing {file}")
                zipf = zipfile.ZipFile(file+'.zip', 'w')
                zipf.write(file, compress_type=zipfile.ZIP_DEFLATED)
                zipf.close()

                self.last_check = check_date
                self.debug("Removing original of archived file")
                remove(file)


def msg_log_edit(date, chat_name, reply_msg_id,
                 user_name, from_id, messg, filepath='.'):
    msg_log = "[{}] [ {} ]\n[{}] {} {} ({}):\n{} {}\n".format(
        date,
        # ^^^ 1 date
        colored("{}".format(chat_name), "green"),
        # ^^^ 2 chat ID      
        colored("{}".format(reply_msg_id), "red"),
        # ^^^ 3 message ID
        colored("{}".format(">>>"), "yellow"),
        colored("{}".format(user_name), "green"),
        # ^^^ 4 display name (i.e John)
        colored("{}".format(from_id), "yellow"), 
        # ^^^ 5 user ID
        colored("{}".format("EDIT"), "yellow"),
        # ^^^ represents new line
        messg)
        # ^^^ user message   
    msg_log = "_"*21+'\n'+msg_log

    dt = datetime.now()
    log_filename = join(filepath, "logs", f"{dt.year}-{dt.month:02}-{dt.day:02}")

    orig = []
    # ^^^ finding original message
    with open(log_filename, "r") as log:
        data = log.read()
        data = data.split("_"*21)
        for full_msg in data:
            msg_parts = full_msg.split('\n')
            for part in msg_parts:
                if str(reply_msg_id) in part:
                    orig.append(full_msg)
                    break
    if orig:
        orig = str(orig[-1])
        pos1 = orig.find('MSG\x1b[0m ')
        if pos1 == -1:
            pos1 = orig.find('EDIT\x1b[0m ')
            orig = orig[pos1+len('EDIT\x1b[0m '):].strip()
        else:
            orig = orig[pos1+len('MSG\x1b[0m '):].strip()
        pos1 = orig.find('!<-dif->!')
        if pos1 != -1:
            orig = orig[:pos1].strip()

        dif = difflib.unified_diff(orig.split(), messg.split())
        dif = ' '.join([x for x in dif])
        dif = '!<-dif->!\n' + dif
        msg_log = msg_log + dif + '\n'
    print(msg_log, end='')
    with open(log_filename, "a+") as log:
        log.write(msg_log)


async def msg_log_chat_action(usr, event, client, utils, filepath='.'):
    dt = datetime.now()

    log_filename = join(filepath, "logs", f"{dt.year}-{dt.month:02}-{dt.day:02}")

    messg = f"{usr.user.first_name} {usr.user.last_name} [@{usr.user.username} {usr.user.id}] "
    if event.user_joined:
        messg += 'joined the group' 
    else:
        messg += 'left the group'
    group = utils.get_display_name(await client.get_entity(event.action_message.to_id))

    messg = colored("{} {}\n".format(messg, group), "red")
    print(messg, end='')
    with open(log_filename, "a+") as log:
        log.write(messg)


def new_msg_log(date, message_id, chat_name, user_name, from_id, messg, filepath='.'):
    msg_log = "[{}] [{}] [ {} ]\n{} {} ({}):\n{} {}\n".format(
        date,
        # ^^^ 1 date
        colored("{}".format(message_id), "red"),
        # ^^^ 2 message ID
        colored("{}".format(chat_name), "green"),
        # ^^^ 3 chat ID               
        colored("{}".format(">>>"), "yellow"),
        # ^^^ 4
        colored("{}".format(user_name), "green"),
        # ^^^ 5 display name (i.e John)
        colored("{}".format(from_id), "yellow"),
        # ^^^ 6 user ID
        colored("{}".format("MSG"), "yellow"),
        # ^^^ 7 represents new line
        messg)
        # ^^^ 8 user message
    msg_log = "_"*21+'\n'+msg_log

    dt = datetime.now()

    print(msg_log, end='')
    log_filename = join(filepath, "logs", f"{dt.year}-{dt.month:02}-{dt.day:02}")
    with open(log_filename, "a+") as log:
        log.write(msg_log)


def msg_reply_log(date, message_id, chat_name, user_name,
                  from_id, reply_to_usr, reply_to_usr_id,
                  reply_msg_id, reply_to_usr_text, messg,
                  filepath='.'):
    msg_log = "[{}] [{}] [ {} ]\n{} {} ({}) TO {} ({}) [{}]:\n{} <{}>\n{} {}\n".format(
        date,
        # ^^^ 1 date
        colored("{}".format(message_id), "red"),
        # ^^^ 2 message ID
        colored("{}".format(chat_name), "green"),
        # ^^^ 3 chat ID               
        colored("{}".format(">>>"), "yellow"),
        # ^^^ 4
        colored("{}".format(user_name), "green"),
        # ^^^ 5 display name (i.e John)
        colored("{}".format(from_id), "yellow"),
        # ^^^ 6 user ID
        colored("{}".format(reply_to_usr), "green"),
        # ^^^ 7 reply user display name
        colored("{}".format(reply_to_usr_id), "yellow"),
        # ^^^ 8 reply user ID
        colored("{}".format(reply_msg_id), "red"),
        # ^^^ 9 reply message ID
        colored("{}".format("QUO"), "yellow"),
        # ^^^ 10 quote indication
        colored("{0}".format(reply_to_usr_text.replace('\n', ' ')), "green"),
        # ^^^ 11 limit reply by characters
        colored("{}".format("MSG"), "yellow"),
        # ^^^ 12 represents new line
        messg)
        # ^^^ 13 user message
    msg_log = "_"*21+'\n'+msg_log

    dt = datetime.now()

    print(msg_log, end='')
    log_filename = join(filepath, "logs", f"{dt.year}-{dt.month:02}-{dt.day:02}")
    with open(log_filename, "a+") as log:
        log.write(msg_log)