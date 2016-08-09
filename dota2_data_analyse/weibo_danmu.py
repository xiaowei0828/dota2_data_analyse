#coding=utf-8

import socket
import re

buffer_size = 1024

address_danmu_1 = ('115.231.96.20', 8601)
login_magic_code_1 = b'\x58\x00\x00\x00\x58\x00\x00\x00\xb1\x02\x00\x00'

address_danmu_2 = ('119.97.145.130', 12602)
login_magic_code_2 = b'\x57\x00\x00\x00\x57\x00\x00\x00\xb1\x02\x00\x00'
join_group_magic_code2 = b'\x2b\x00\x00\x00\x2b\x00\x00\x00\xb1\x02\x00\x00'

#address = ('119.97.145.130', 843)
#s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
#s.connect(address)
#print(s)
#first_data = b'<policy-file-request/>'
#s.send(first_data)
#recv_data = s.recv(buffer_size)
#print(recv_data)
#s.close()

info_pattern = re.compile('nn@=(.*?)/txt@=(.*?)/')

def parse_data(data):
    data_str = data[8:-1].decode()
    print(data_str)
    if 'type@=error/code@=51/' == data_str:
        print('some error occurs, re-login')
        login_and_get_data()
        return

    matches = info_pattern.findall(data_str)
    for match in matches:
        print(match[0] + ' : ' + match[1])

def login_and_get_data():
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect(address_danmu_2)

    login_data = login_magic_code_2 + b'type@=loginreq/username@=qq_3HybyZDK/password@=1234567890123456/roomid@=97376/\x00'

    s.send(login_data)
    recv_data = s.recv(buffer_size)
    print(recv_data)

    join_group = join_group_magic_code2 + b'type@=joingroup/rid@=97376/gid@=1/\x00'
    s.send(join_group)

    len = int(0)

    while True:
        try:
            data_len_bytes = s.recv(4)
            data_len = int.from_bytes(data_len_bytes, byteorder='little')
            data = s.recv(data_len)
            parse_data(data)
        except:
            print('some exception occurs, re-login')
            login_and_get_data()
            return

login_and_get_data()