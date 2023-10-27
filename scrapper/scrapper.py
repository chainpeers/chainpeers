import subprocess
import threading
import os
import time
from requests import Session as ReqSession
import requests
import gzip
import json
from node_functions import get_enode_from_id, check_node_line, rlpx_ping_call_and_unpack


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
        #  file with starting peers
        with open(str(json_loc), 'r', encoding='utf-8') as f:
            f = f.read()
            text = json.loads(f)
            for i in text:
                payload += (f'{{"address":"{text[i]["record"]}",'
                            f'"version":"{text[i]["seq"]}","score":"{text[i]["score"]}"}},')

            payload = payload[:len(payload) - 1]
            payload = '[' + payload + ']'
            full_url = self.address + '/' + name_request
            payload = {
                "time": f'{time.time()}',
                "starting_peers": payload,
                "chain": "my_chain"
            }
            compressed_payload = gzip.compress(json.dumps(payload).encode('utf-8'))
            self.slice_id = str(eval(requests.post(full_url, data=compressed_payload).text)['id'])
            print(self.slice_id)

        self.proc = subprocess.Popen([dev_loc, "--log.format=json", "--verbosity=4",
                                      log_loc, "discv4", "crawl", json_loc],
                                     stdout=subprocess.PIPE,
                                     stderr=subprocess.STDOUT,
                                     universal_newlines=True)

        self.is_running = True
        register_list = ''
        peer_count = 0
        name_request = "register_peers"
        batch_size = self.batch_size
        req_session = ReqSession()
        #  main send cycle. soon to be changed completely
        for line in self.proc.stdout:
            processed_line = json.loads(line)
            if check_node_line(processed_line):
                node_address = get_enode_from_id(processed_line['id'], dev_loc)
                try:
                    info_pack = rlpx_ping_call_and_unpack(node_address[:-1], dev_loc)
                    version = info_pack['version']
                    client = info_pack['client']
                    client_version = info_pack['client_version']
                    caps = info_pack['caps']
                # to do: add exception    
                except:
                    version = None

                register_list += (f'{{"address":"{node_address[:-1]}",'
                                  f'"version":"{version}",'
                                  f'"score":"{processed_line["score"]}"}},')
                peer_count += 1

            if peer_count >= batch_size:
                self.data_send(req_session, register_list, name_request)
                peer_count = 0
        self.proc.wait()

    def crawl_stop_by_press(self):
        #  gonna be deleted
        input("Press Enter to stop process...")
        if self.proc:
            self.proc.terminate()
        self.is_running = False

    def data_send(self, req_ses, data, place):
        register_list = data[:len(data) - 1]
        register_list = '[' + register_list + ']'
        payload = {"slice_id": self.slice_id,
                   "peer_list": register_list,
                   "time": f'{time.time()}'}
        full_url = self.address + "/" + place
        compressed_payload = gzip.compress(json.dumps(payload).encode('utf-8'))
        req_ses.post(full_url, data=compressed_payload)


crawl_proc = CrawlerProcess()

#  going to be deleted
process_thread = threading.Thread(target=crawl_proc.run_process)
close_thread = threading.Thread(target=crawl_proc.crawl_stop_by_press)

process_thread.start()
close_thread.start()
process_thread.join()
close_thread.join()


