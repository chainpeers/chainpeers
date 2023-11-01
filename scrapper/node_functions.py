import subprocess
import json


def check_node_line(json_line):
    # original devp2p crawl output handler
    first_key = list(json_line.keys())[0]  # |
    forth_key = list(json_line.keys())[3]  # | check if node info
    is_first_key_id = (first_key == 'id')  # |
    is_forth_key_score = (forth_key == 'score')  # |
    return is_first_key_id and is_forth_key_score


def get_enode_from_id(id_node, dev_loc):
    with open('key.txt', 'w', encoding='utf-8') as enr_id:  # to-enode works only with file
        enr_id.write(str(id_node))
    node_address = subprocess.check_output([dev_loc, 'key', 'to-enode', 'key.txt'], text=True)  # key to enode
    return node_address



