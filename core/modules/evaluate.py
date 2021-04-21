from multiprocessing import Process, Queue, Manager
import traceback
import re


class Executor:

    command = 'eval'
    use_call_name = False

    def __init__(self, config, debugger):
        self.config = config
        self.debug = debugger

    def help(self):
        return f"Eval:\n  %s 2+2" % self.command

    def run_pre_check(self, text: str) -> str:
        """
        Check command for 'print' or 'len'.
        Simulate 'print' or 'len' and return the result.
        Direct execution of eval is not allowed.
        """
        result = None

        if "print" in text.lower():
            self.debug("Found print in eval expression")
            findres = text.find("print(")
            rfindres = text.find(")", findres)
            if findres != -1 and rfindres != -1:
                result = text[(findres + 6):rfindres]
                result = result.replace('"', '')  
        elif "len" in text.lower():
            self.debug("Found len in eval expression")
            findres = text.find("len(")
            rfindres = text.find(")", findres)
            if findres != -1 and rfindres != -1:
                result = text[(findres + 4):rfindres]
                result = result.replace('"', '')
                result = str(len(result))
        self.debug(f"Result: {result}")
        return result

    def evaluater(self, expression: str, ev_dict: dict):
        """
        Strip the string from non-math characters.
        Execute eval of the stripped string.
        """
        # accepts shared dict
        ev_dict['RES'] = 'Error'
        regex = re.compile(r'[^\d\.\*\+\-\/\(\)]')
        expression = regex.sub('', expression)
        result = str(eval(expression, {'__builtins__': None}))
        # isolate eval from access to the scope ^^^^^^^^^
        ev_dict['RES'] = result
        # if eval does not succeed, result will not be set.
        # 'Error' will be displayed instead.

    def run_multiprocess(self, text: str) -> str:
        """
        Run a shared dictionary instance to accept the value of the result.
        Run a separate process with eval execution.
        Terminate it in case it's stuck.
        """
        if len(text) < len("_eval"):
            return
        expression = text.replace(f"{self.config.S}eval", '')
        if '🔟' in expression:
            expression = expression.replace('🔟', '10')
        if '🔢' in expression:
            expression = expression.replace('🔢', '1234')
        expression = expression.strip()
        if len(str(expression)) >= 40:
            return "Sorry, your expression is too long."
        else:
            manager = Manager()
            ev_dict = manager.dict()
            try:
                proc = Process(target=self.evaluater, args=(expression, ev_dict,))
                proc.daemon = True
                proc.start()
                self.debug(f"Started new process: {proc}")
                
                proc.join(3)
                if proc.is_alive():
                    self.debug("Eval was terminated")
                    proc.terminate()
                print("Eval status: ", proc, ev_dict)
                return ev_dict['RES']
            except:
                self.debug(str(traceback.print_exc()))
                return

    async def call_executor(self, event):
        try:
            out = self.run_pre_check(event.raw_text)
            if out:
                await event.reply(out)
            else:
                out = self.run_multiprocess(event.raw_text)
                if out:
                    await event.reply(out)
        except:
            self.debug(traceback.print_exc())
