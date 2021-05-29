from multiprocessing import Process, Manager
from typing import Union
import asyncio
import traceback
import re


class Executor:

    command = 'eval'
    use_call_name = False

    def __init__(self, config, debugger):
        self.config = config
        self.debug = debugger

    def help(self):
        return "Eval:\n  %s 2+2" % self.command

    def parse_eval(self, text):
        if len(text) < len("_eval"):
            return
        if len(str(text)) >= 120:
            return 1, 'Whoa, this expression is so big ( ͡° ͜ʖ ͡°)'
        expression = text.replace(f"{self.config.S}eval", '').strip()
        if '🔟' in expression:
            expression = expression.replace('🔟', '10')
        if '🔢' in expression:
            expression = expression.replace('🔢', '1234')

        blacklist = [
            r'__.*?__',
            r'os\.',
            r'sys\.',
            r'\.?system',
            r'\.class',
            r'\.name',
            r'\.base',
            r'\.subclasses',
            r'\.dump'
            'builtins',
            'builtinimporter',
            'globals',
            'locals',
            'load_module',
            'exec',
            'eval',
            'chr',
            'ord',
            'getattr',
            'setattr',
            'input',
            'bash ',
            'import ',
        ]
        sub_rules = '(' + '|'.join(blacklist).strip('|') + ')'
        expression = re.sub(sub_rules, '_', expression, flags=re.IGNORECASE)

        check_range = re.findall(r'range\((\d+)\)', expression)
        if check_range:
            for _range in check_range:
                if int(_range) > 50:
                    expression = re.sub(r'range\(%d\)' % int(_range), 'range(50)', expression)

        expression = re.sub(r'print\(', 'str(', expression)
        # properly check for unmatched quotes
        expression = re.sub(r'str\((\'|\")(.*)(\'|\")\)', r'"\g<2>"', expression)

        self.debug("Eval end result: %s" % expression)
        return expression.strip()

    def evaluater(self, expression: str, ev_dict: dict) -> None:
        """
        Strip the string from non-math characters.
        Execute eval of the stripped string.
        """
        # accepts shared dict
        ev_dict['RES'] = 'Invalid syntax'

        isolation = {
            'globals': None,
            'locals': None,
            '__name__': None,
            '__file__': None
        }

        try:
            result = str(eval(expression, isolation))
        except Exception as e:
            self.debug('Eval failed with %s' % e)
            return
        # if eval does not succeed, result will not be set.
        # 'Error' will be displayed instead.
        ev_dict['RES'] = result

    def run_multiprocess(self, text: str) -> Union[str, None]:
        """
        Run a shared dictionary instance to accept the value of the result.
        Run a separate process with eval execution.
        Terminate it in case it's stuck.
        """
        expression = self.parse_eval(text)
        if not expression:
            return
        if type(expression) is tuple:
            return expression[1]

        manager = Manager()
        ev_dict = manager.dict()
        try:
            proc = Process(target=self.evaluater, args=(expression, ev_dict,))
            proc.daemon = True
            proc.start()
            self.debug("Started new process: %s" % str(proc))

            proc.join(3)
            if proc.is_alive():
                proc.terminate()
                self.debug("Eval has been terminated")

            return ev_dict['RES']
        except:
            self.debug(str(traceback.print_exc()))
            return

    async def call_executor(self, event):
        try:
            loop = asyncio.get_event_loop()
            out = await loop.run_in_executor(None, self.run_multiprocess, event.raw_text)
            if out:
                if len(out) <= 2048:
                    await event.reply(out)
                    return
        except:
            self.debug(traceback.print_exc())
