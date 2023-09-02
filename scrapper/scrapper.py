import subprocess
import argparse
import threading

parser = argparse.ArgumentParser()
parser.add_argument("-l", "--logloc", type=str)
parser.add_argument("-j", "--jsonloc", type=str)
args = parser.parse_args()
log_loc = "--log.file=" + args.logloc
json_loc = args.jsonloc


class MyProcess:
    def __init__(self):
        self.proc = None

    def run_process(self):
        self.proc = subprocess.Popen(["./go-ethereum/build/bin/devp2p", "--log.format=json", "--verbosity=5",log_loc, "discv4","crawl",json_loc])
        self.proc.communicate()

    def get_input(self):
        input("Press Enter to stop process...")
        if self.proc:
            self.proc.terminate()


my_proc = MyProcess()


process_thread = threading.Thread(target=my_proc.run_process)
process_thread.start()

my_proc.get_input()
