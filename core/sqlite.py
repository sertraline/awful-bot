from datetime import datetime
import sqlite3
import os

class SqliteInterface():

    def __init__(self, debug):
        self.debug = debug

        self.init_db()
        self.clear_queue()


    def commit(self):
        self.debug("Commit()")
        self.conn.commit()
    

    def execute(self, query):
        self.debug(query)
        _out = self.cursor.execute(query)
        return _out


    def init_db(self):
        if not os.path.isfile('bot.db'):
            with open('bot.db', 'w'):
                pass

        self.conn = sqlite3.connect("bot.db")
        self.cursor = self.conn.cursor()

        query_list = [
            # future_queue: data which awaits user confirmation for output,
            # e.g command <next> in the chat to pull out closest row
            # with current (user_id and chat_id) from the table.
            ("CREATE TABLE future_queue "
                 "(user_id integer, chat_id integer, user_data text, method text, "
                 "keywords text, msg_id integer)"),
            # If data is too big for a single message, it is splitted into parts. 
            # 
            # Full data is pushed to current_queue.
            # Parts are pushed to future_queue and sent when user asks for <next>.
            #
            # current_queue is queried when user makes a selection,
            # e.g <get 1> or <get 2> in the chat to select first or second
            # item from numerated list.
            ("CREATE TABLE current_queue "
                 "(user_id integer, chat_id integer, user_data text, method text, "
                 "keywords text, selection text, msg_id integer, child_ids text)"),
            # call_stack: list of user IDs encountered by bot.
            ("CREATE TABLE call_stack "
                 "(user_id integer, user_name text, last_seen text)"),
            ("CREATE TABLE blacklist "
                 "(user_id integer)"),
            ("CREATE TABLE whitelist "
                 "(user_id integer)"),
            ("CREATE TABLE image_tracker "
                 "(user_id integer)"),
            ("CREATE TABLE voice_tracker "
                 "(user_id integer)"),
            ("CREATE TABLE msg_tracker "
                 "(user_id integer)")]

        for query in query_list:
            try:
                self.execute(query)
            except sqlite3.OperationalError:
                continue

        self.commit()


    def insert_call_stack(self, user_id, user_name):
        last_seen = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        query = ("SELECT EXISTS(SELECT 1 FROM call_stack "
                 f"WHERE user_id={user_id})")
        _output = self.execute(query)

        if _output.fetchall()[0][0] == 1:
            query = (f"UPDATE call_stack SET user_id={user_id}, "
                     f"user_name='{user_name}', last_seen='{last_seen}' "
                     f"WHERE user_id={user_id}")
            self.execute(query)

            self.commit()
            return

        query = (f"INSERT INTO call_stack "
                 "(user_id, user_name, last_seen) VALUES "
                 f"({user_id}, '{user_name}', '{last_seen}')")

        self.execute(query)
        self.commit()


    def fetch_call_stack(self, limit=None):
        order = 'DESC'
        if limit:
            order += f'Limit {limit}'
        
        query = ("SELECT * FROM call_stack "
                 f"ORDER BY datetime(last_seen) {order}")
        
        _output = self.execute(query)
        return _output


    def clear_queue(self):
        query = "DELETE FROM current_queue"
        self.execute(query)

        query = "DELETE FROM future_queue"
        self.execute(query)

        self.commit()


    def clear_user_queue(self, user_id, chat_id=None):
        if not chat_id:
            chat_id = user_id

        query = (f"DELETE FROM current_queue WHERE user_id={user_id} "
                 f"AND chat_id={chat_id}")
        self.execute(query)

        query = f"DELETE FROM future_queue WHERE user_id={user_id} AND chat_id={chat_id}"
        self.execute(query)

        self.commit()


    def check_current_queue(self, user_id, keywords=None,
                            chat_id=None, msg_id=None):
        if not chat_id:
            chat_id = user_id

        _and_block = f"AND chat_id={chat_id}"
        if msg_id:
            _and_block += f" AND msg_id={msg_id}"
        elif keywords:
            _and_block += f" AND keywords='{keywords}'"

        query = ("SELECT EXISTS(SELECT 1 FROM current_queue "
                 f"WHERE user_id={user_id} {_and_block})")
        _output = self.execute(query)

        if _output.fetchall()[0][0] == 1:
            return True
        
        if msg_id:
            query = ("SELECT EXISTS(SELECT 1 FROM current_queue "
                    f"WHERE user_id={user_id} AND chat_id={chat_id} "
                    f"AND child_ids LIKE '%{msg_id}%')")
            _output = self.execute(query)

            if _output.fetchall()[0][0] == 1:
                return True
        return False


    def insert_current_queue(self, user_id, user_data, method,
                             keywords, msg_id, selection='', chat_id=None):
        if not chat_id:
            chat_id = user_id

        check = self.check_current_queue(user_id, keywords, chat_id)
        if not check:
            query = ("INSERT INTO current_queue "
                    f"(user_id, chat_id, user_data, method, "
                    "keywords, selection, msg_id) VALUES "
                    f"({user_id}, {chat_id}, '{user_data}', "
                    f"'{method}', '{keywords}', '{selection}', '{msg_id}')")
        else:
            query = (f"UPDATE current_queue SET "
                     f"user_id={user_id}, chat_id={chat_id}, "
                     f"user_data='{user_data}', method='{method}', keywords='{keywords}', "
                     f"selection='{selection}', msg_id={msg_id} WHERE "
                     f"user_id={user_id} AND keywords='{keywords}'")
        self.execute(query)

        self.commit()


    def add_childs_current_queue(self, child_id, root_id):
        query = ("SELECT * FROM current_queue "
                 f"WHERE msg_id={root_id}")
        _out = self.execute(query).fetchall()

        if not _out[0][7]:
            query = (f"UPDATE current_queue SET child_ids='{child_id}'")
        else:
            conc = _out[0][7]+','+child_id
            query = (f"UPDATE current_queue SET child_ids='{conc}'")
        self.execute(query)
        self.commit()


    def check_future_queue(self, user_id, chat_id=None):
        if not chat_id:
            chat_id = user_id

        query = ("SELECT EXISTS(SELECT 1 FROM future_queue "
                 f"WHERE user_id={user_id} AND chat_id={chat_id})")
        _output = self.execute(query)

        if _output.fetchall()[0][0] == 1:
            return True
        return False


    def fetch_current_queue(self, user_id, chat_id=None,
                            msg_id=None, keywords=None):
        if not chat_id:
            chat_id = user_id

        _and_block = f" AND chat_id={chat_id}"
        if msg_id:
            _and_block += f" AND msg_id={msg_id}"
        elif keywords:
            _and_block += f" AND keywords='{keywords}'"

        query = (f"SELECT * FROM current_queue WHERE user_id={user_id}"
                 f"{_and_block}")
        _output = self.execute(query).fetchall()

        if not _output and msg_id:
            query = (f"SELECT * FROM current_queue WHERE user_id={user_id} "
                     f"AND chat_id={chat_id} AND child_ids LIKE '%{msg_id}%'")
            _output = self.execute(query).fetchall()
        return _output


    def insert_future_queue(self, user_id, user_data,
                            method, keywords, msg_id,
                            chat_id=None):
        if not chat_id:
            chat_id = user_id

        query = (f"INSERT INTO future_queue "
                 "(user_id, chat_id, user_data, method, keywords, msg_id) VALUES "
                 f"({user_id}, {chat_id}, '{user_data}', '{method}', '{keywords}', {msg_id})")
        self.execute(query)

        self.commit()


    def fetch_next_from_queue(self, user_id, chat_id=None):
        if not chat_id:
            chat_id = user_id

        query = ("SELECT rowid, * FROM future_queue WHERE "
                 "rowid=(SELECT MIN(rowid) FROM future_queue) "
                 f"AND user_id={user_id} AND chat_id={chat_id}")
        _output = self.execute(query)
        _output = _output.fetchall()

        rowid = _output[0][0]
        data = _output[0][3]
        root_id = _output[0][6]

        query = f"DELETE FROM future_queue WHERE rowid={rowid}"
        self.execute(query)

        self.commit()
        return data, root_id


    def check_lists_queue(self, type_list, user_id):
        query = f"SELECT EXISTS(SELECT 1 FROM {type_list} WHERE user_id={user_id})"
        _output = self.execute(query)

        if _output.fetchall()[0][0] == 1:
            return True
        return False


    def check_whitelist(self):
        query = "SELECT * FROM whitelist"
        check = self.execute(query)

        if not check.fetchall():
            return False
        return True


    def insert_one_column_list(self, list_type, user_id):
        check = self.check_lists_queue(list_type, user_id)

        if check:
            query = f"DELETE FROM {list_type} WHERE user_id={user_id}"
            self.execute(query)
            self.commit()
            return False

        query = f"INSERT INTO {list_type} (user_id) VALUES ({user_id})"
        self.execute(query)
        self.commit()
        return True


    def fetch_from_list(self, list_type):
        query = f'SELECT * FROM {list_type}'
        _out = self.execute(query)

        return _out.fetchall()