import subprocess
import threading
import os
import time
import requests
import json
import zlib
import json
import logging

MAIN_URL = "http://localhost:8000"

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
        self.is_running = False
        self.slice_id = None

    def run_process(self):
        name_request = 'start_slice'
        payload = ''
        with open(str(json_loc), 'r', encoding='utf-8') as f:  # открыли файл с данными
            f = f.read()
            text = json.loads(f)
            c = 0
            print(len(text))
            for i in text:
                payload += f'{{"address":"{text[i]["record"]}","version":"{text[i]["seq"]}","score":"{text[i]["score"]}"}},'

            payload = payload[:len(payload) - 1]
            payload = '[' + payload + ']'
            # print(payload)
            full_url = MAIN_URL + '/' + name_request  # Замените на свой URL
            payload = {
                "time": f'{time.time()}',
                "starting_peers": payload,
                "chain": "my_chain"
            }
            self.slice_id = str(eval(requests.post(full_url, json=payload).text)['id'])
            print(self.slice_id)

        self.proc = subprocess.Popen([dev_loc, "--log.format=json", "--verbosity=4",
                                      log_loc, "discv4", "crawl", json_loc])

        self.is_running = True
        self.data_send()
        self.proc.communicate()

    def get_input(self):
        input("Press Enter to stop process...")
        if self.proc:
            self.proc.terminate()
        self.is_running = False

    import time
    import subprocess
    import requests
    import json
    import zlib

    def data_send(self):
        name_request = "register_peers"
        time_step = 0.2
        batch_size = 10  # Number of log entries to include in each batch
        log_entries = []  # List to store log entries for batching

        while self.is_running:
            was = time.time()
            # every time_step seconds
            while time.time() - was < time_step:
                pass
            else:
                with open('logs.json', 'r+', encoding='utf-8') as logfile:
                    register_list = ''
                    while 1:
                        # read log
                        logline = logfile.readline()
                        if not logline:
                            break
                        logline = json.loads(logline)  # turn log line string to dict
                        # if 0 is id and 3 is score
                        first_key = list(logline.keys())[0]
                        forth_key = list(logline.keys())[3]
                        is_first_key_id = (first_key == 'id')
                        is_forth_key_score = (forth_key == 'score')
                        if is_first_key_id and is_forth_key_score:
                            subprocess.run([dev_loc, 'key', 'generate', 'key.txt'])
                            with open('key.txt', 'w', encoding='utf-8') as enr_id:
                                # write id from log to a txt
                                enr_id.write(logline['id'])
                            node_address = subprocess.check_output([dev_loc, 'key', 'to-enode', 'key.txt'], text=True)
                            register_list += f'{{"address":"{node_address[:-2]}","version":"{logline["seq"]}","score":"{logline["score"]}"}},'  # [:-2] key to enode makes logs with /n

                        # Add log entry to batch
                        log_entries.append(logline)

                        # Check if batch size is reached
                        if len(log_entries) >= batch_size:
                            # Prepare batch for sending
                            register_list = register_list[:len(register_list) - 1]  # remove last comma
                            register_list = '[' + register_list + ']'
                            payload = {"slice_id": self.slice_id,
                                       "peer_list": register_list,
                                       "time": f'{time.time()}'}
                            full_url = MAIN_URL + "/" + name_request
                            # compress payload
                            compressed_payload = zlib.compress(json.dumps(payload).encode('utf-8'))
                            # send post
                            requests.post(full_url, data=compressed_payload)

                            # Clear log entries for the next batch
                            log_entries = []
                            register_list = ''

                    # Truncate the log file after processing all entries
                    logfile.truncate()


crawl_proc = CrawlerProcess()
process_thread = threading.Thread(target=crawl_proc.run_process)
close_thread = threading.Thread(target=crawl_proc.get_input)

process_thread.start()
close_thread.start()
process_thread.join()
close_thread.join()




