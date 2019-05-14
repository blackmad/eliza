import os 
import readline
import atexit
from eliza import Eliza

import logging
log = logging.getLogger(__name__)
#log.level = logging.DEBUG

class ElizaConsole:
    def __init__(self, config_file):
        self.HISTORY_FILENAME = os.path.expanduser('~/.eliza_history')
        self.init_history(self.HISTORY_FILENAME)
        self.eliza = Eliza(config_file)

    def run(self):
        print(self.eliza.initial())

        while True:
            try:
                sent = input('> ')
            except EOFError:
                break

            output = self.eliza.respond(sent)
            if output is None:
                break

            print(output)

        print(self.eliza.final())

    def init_history(self, histfile):
        readline.parse_and_bind("tab: complete")
        if hasattr(readline, "read_history_file"):
            try:
                readline.read_history_file(histfile)
            except IOError:
                pass
            atexit.register(self.save_history, histfile)

    def save_history(self, histfile):
        readline.set_history_length(1000)
        readline.write_history_file(histfile)

ConfigFile = 'doctor.txt'

from watchdog.events import FileSystemEventHandler
class MyHandler(FileSystemEventHandler):
    def __init__(self, eliza):
        self.eliza = eliza

    def on_modified(self, event):
        #print(f'event type: {event.event_type}  path : {event.src_path}')
        if os.path.abspath(event.src_path) == os.path.abspath(ConfigFile):
            print('reloading config')
            self.eliza.load(ConfigFile)

def main():
    elizaConsole = ElizaConsole(config_file=ConfigFile)

    from watchdog.observers import Observer
    from watchdog.events import LoggingEventHandler

    observer = Observer()
    observer.schedule(MyHandler(elizaConsole.eliza), '.', recursive=False)
    observer.start()

    elizaConsole.run()

if __name__ == '__main__':
    logging.basicConfig()
    main()