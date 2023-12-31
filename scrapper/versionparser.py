import subprocess
import json


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
