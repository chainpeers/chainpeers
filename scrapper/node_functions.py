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


def rlpx_ping_call_and_unpack(address, dev_loc):
    info_pack = subprocess.check_output([dev_loc, 'rlpx', 'ping', address], timeout=1000, text=True)
    info_pack = info_pack.strip()
    info_pack = info_pack.replace('Version:', '"Version":')
    info_pack = info_pack.replace('Name:', '","Name":')
    info_pack = info_pack.replace('Caps:', '","Caps":')
    info_pack = info_pack.replace('ListenPort:', '","ListenPort":')
    info_pack = info_pack.replace('ID:', '","ID":')
    info_pack = info_pack.replace('Rest:', '","Rest":')
    info_pack = info_pack.replace(':', ':"')
    info_pack = info_pack.replace(' "', '"')
    info_pack = info_pack.replace('}', '"}')
    info_pack = json.loads(info_pack)
    name_stops_at = info_pack["Name"].index('/')
    data = {"version": info_pack["Version"],
            "client": info_pack["Name"][:name_stops_at],
            "client_version": info_pack["Name"][name_stops_at:],
            "caps": info_pack["Caps"]}
    return data
