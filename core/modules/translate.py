from googletrans import Translator
from datetime import datetime, timedelta


class Executor:

    FLAGLIST = {
        "ru": "🇷🇺",
        "ja": "🇯🇵", 
        "en": "🇬🇧",
        "uk": "🇩🇪", 
        "pl": "🇩🇪",
        "de": "🇩🇪", 
        "fr": "🇫🇷",
        "no": "🇳🇴",
        "es": "🇪🇸",
        "fi": "🇫🇮",
        "hy": "🇦🇲",
        "pt": "🇧🇷",
        "ar": "🇸🇦🇪🇬",
        "zh": "🇨🇳",
        "cs": "🇨🇿",
        "el": "🇬🇷",
        "he": "🇮🇱",
        "it": "🇮🇹",
        "hr": "🇷🇸+🇲🇪=<3"
    }

    command = 'tr'
    # placeholders: list of all values you expect to see in the beginning of command
    placeholders = [key for key in FLAGLIST.keys()]
    use_call_name = False

    DELAY = [None, None]

    def __init__(self, config, debugger):
        self.config = config
        self.debug = debugger

    def help(self):
        gt_langlist = str([x for x in self.FLAGLIST.keys()])
        gt_langlist = gt_langlist.replace("'", "")

        return ("Translator:\n"
                f"Languages list:\n  {gt_langlist}\n"
                "Usage:\n"
                f"  {self.config.S}tren text\n"
                f"  {self.config.S}trpl Poland can into space\n"
                "Reply to any message with command to translate it.")

    def translate_string(self, user_text: str, language: str,
                         reply: str) -> str:
        translator = Translator()
        if user_text.startswith('`'):
            user_text = user_text.replace('`', '')
        print(user_text, reply)

        for lng in self.FLAGLIST.values():
            if lng in user_text:
                user_text = user_text.replace(lng, '')

        if user_text.strip():
            self.debug("Found user text; translating...")
            translated = translator.translate(user_text, dest=language)
        else:
            if reply:
                self.debug("Translating user reply...")

                if reply.startswith('`'):
                    reply = reply.replace('`', '')
                for lng in self.FLAGLIST.values():
                    if lng in reply:
                        reply = reply.replace(lng, '')

                reply = str(reply).strip()
                translated = translator.translate(reply, dest=language)
            else:
                self.debug("No message found, returning informative message")
                langlist = [key for key in self.FLAGLIST.keys()]
                langlist = str(langlist).replace("'", "")

                return ("```Languages list:\n"
                        f"  {langlist}\n"
                        "Usage:\n"
                        f"  {self.config.S}trpl Poland can into space```")

        sourceflag = ' '  # source emoji
        destflag = ' '    # destination emoji

        for language in self.FLAGLIST:
            if language in translated.src:
                sourceflag = self.FLAGLIST[language]
            if language in translated.dest:
                destflag = self.FLAGLIST[language]

        if translated.pronunciation and len(translated.pronunciation) < 20:
            # if there is available pronunciation; limit to short phrases
            return (f"```[{sourceflag} {translated.src}] ➜ "
                    f"[{destflag} {translated.dest}]:\n"
                    f"{translated.text}\n"
                    f"PRONUN: {translated.pronunciation}```")
        else:
            if translated.text.strip():
                return (f"```[{sourceflag} {translated.src}] ➜ "
                        f"[{destflag} {translated.dest}]:\n"
                        f"{translated.text}```")

    async def call_executor(self, event, client, key):
        _start = self.config.S
        lang = None

        for language in self.FLAGLIST.keys():
            if event.raw_text.lower().startswith(f"{_start}tr{language}"):
                lang = language
                break
        if not lang:
            return

        reply_to_usr_text = ''
        if event.message.reply_to_msg_id:
            reply_msg_id = event.message.reply_to_msg_id
            async for msg in client.iter_messages(event.to_id,
                                                  max_id=reply_msg_id+1,
                                                  min_id=reply_msg_id-1):
                if msg.id == reply_msg_id:
                    if not msg.media:
                        reply_to_usr_text = msg.text
                        break

        txt = event.raw_text.replace(key+language, '')

        translated = self.translate_string(txt, language, reply_to_usr_text)

        if translated.startswith('```Languages list:\n  '):
            TDELTA, TDELTA_ID = self.DELAY
            if TDELTA and TDELTA_ID:
                if datetime.now() < TDELTA and TDELTA_ID == event.message.to_id:
                    self.debug("Skipping the message due to delay")
                    return
            self.DELAY[0] = datetime.now() + timedelta(seconds=30)
            self.DELAY[1] = event.message.to_id

        await event.reply(translated)
