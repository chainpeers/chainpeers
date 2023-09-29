import subprocess
import threading
import os
import time
from requests import Session as ReqSession
import requests
import gzip
import json


if os.environ.get('logloc') is not None:
    log_path = os.environ.get('logloc')
    log_loc = "--log.file=" + log_path
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
        with open('scrapper_settings.json', 'r', encoding='utf-8') as settings:
            settings = settings.read()
            settings = json.loads(settings)
            self.batch_size = settings['batch_size']
            self.request_delay = settings['request_delay']
            self.address = settings['address']

        self.proc = None
        self.is_running = False
        self.slice_id = None

    def run_process(self):
        name_request = 'start_slice'
        payload = ''
        with open(str(json_loc), 'r', encoding='utf-8') as f:  # открыли файл с данными
            f = f.read()
            text = json.loads(f)
            print(len(text))
            for i in text:
                payload += (f'{{"address":"{text[i]["record"]}",'
                            f'"version":"{text[i]["seq"]}","score":"{text[i]["score"]}"}},')

            payload = payload[:len(payload) - 1]
            payload = '[' + payload + ']'
            # print(payload)
            full_url = self.address + '/' + name_request  # Замените на свой URL
            payload = {
                "time": f'{time.time()}',
                "starting_peers": payload,
                "chain": "my_chain"
            }
            compressed_payload = gzip.compress(json.dumps(payload).encode('utf-8'))
            self.slice_id = str(eval(requests.post(full_url, data=compressed_payload).text)['id'])
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

    def data_send(self):
        name_request = "register_peers"
        time_step = self.request_delay
        batch_size = self.batch_size
        log_entries = []
        req_session = ReqSession()

        while self.is_running:
            time.sleep(time_step)
            with open(log_path, 'r+', encoding='utf-8') as logfile:
                register_list = ''
                while 1:
                    logline = logfile.readline()
                    if not logline:
                        break
                    logline = json.loads(logline)
                    first_key = list(logline.keys())[0]
                    forth_key = list(logline.keys())[3]
                    is_first_key_id = (first_key == 'id')
                    is_forth_key_score = (forth_key == 'score')
                    if is_first_key_id and is_forth_key_score:
                        subprocess.run([dev_loc, 'key', 'generate', 'key.txt'])
                        with open('key.txt', 'w', encoding='utf-8') as enr_id:
                            enr_id.write(logline['id'])
                        node_address = subprocess.check_output([dev_loc, 'key', 'to-enode', 'key.txt'], text=True)
                        register_list += (f'{{"address":"{node_address[:-2]}",'
                                          f'"version":"{logline["seq"]}",'
                                          f'"score":"{logline["score"]}"}},')
                    log_entries.append(logline)
                    if len(log_entries) >= batch_size:
                        register_list = register_list[:len(register_list) - 1]
                        register_list = '[' + register_list + ']'
                        payload = {"slice_id": self.slice_id,
                                   "peer_list": register_list,
                                   "time": f'{time.time()}'}
                        full_url = self.address + "/" + name_request
                        compressed_payload = gzip.compress(json.dumps(payload).encode('utf-8'))
                        req_session.post(full_url, data=compressed_payload)
                        log_entries = []
                        register_list = ''
                logfile.truncate()


crawl_proc = CrawlerProcess()
process_thread = threading.Thread(target=crawl_proc.run_process)
close_thread = threading.Thread(target=crawl_proc.get_input)

process_thread.start()
close_thread.start()
process_thread.join()
close_thread.join()




