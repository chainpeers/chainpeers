import subprocess
import threading
import os


if os.environ.get('logloc') is not None:
    log_loc = "--log.file=" + os.environ.get('logloc')
else:
    print('logloc in not set')
if os.environ.get('jsonloc') is not None:
    json_loc = os.environ.get('jsonloc')
else:
    print('jsonloc in not set')
if os.environ.get('devloc') is not None:
    dev_loc = '.' + os.environ.get('devloc')
else:
    print('devloc is not set')


class CrawlerProcess:
    def __init__(self):
        self.proc = None

    def run_process(self):
        self.proc = subprocess.Popen([dev_loc, "--log.format=json", "--verbosity=5",
                                      log_loc, "discv4", "crawl", json_loc])
        self.proc.communicate()

    def get_input(self):
        input("Press Enter to stop process...")
        if self.proc:
            self.proc.terminate()


my_proc = CrawlerProcess()


process_thread = threading.Thread(target=my_proc.run_process)
process_thread.start()

my_proc.get_input()
