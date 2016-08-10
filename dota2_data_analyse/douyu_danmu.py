#coding=utf-8

import socket
import re
import time
import hashlib
import uuid
import threading
import urllib
import urllib.request
import urllib.parse
import http.cookiejar
import json
import ssl
import os

headers = { 'User-Agent' : 'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/49.0.2623.87 Safari/537.36'}

douyu_cookie_file = 'douyu_cookie'

douyu_host_url = 'http://www.douyu.com/'
room_id = '58428'
buffer_size = 1024

address_danmu_1 = ('danmu.douyutv.com', 8601)

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

def get_douyu_msg(content):
    length = bytearray([len(content) + 9, 0x00, 0x00, 0x00])
    code = length
    magic = bytearray([0xb1, 0x02, 0x00, 0x00])
    end = bytearray([0x00])
    return length + code + magic + bytes(content.encode('utf-8')) + end

def parse_danmu_data(data_str):
    if 'type@=error/code@=51/' == data_str:
        print('some error occurs, re-login')
        return False

    matches = info_pattern.findall(data_str)
    for match in matches:
        try:
            print(match[0]+ ' : ' + match[1])
        except:
            print('Some special character in the message')

    return True

def parse_auth_reponse_data(data):
    pass

def get_danmu(room_id, group_id):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect(address_danmu_1)

    login_data = 'type@=loginreq/username@=qq_3HybyZDK/password@=1234567890123456/roomid@=' + room_id + '/'

    s.send(get_douyu_msg(login_data))
    recv_data = s.recv(buffer_size)
    print(recv_data)

    join_group = 'type@=joingroup/rid@=' + room_id + '/gid@=' + group_id + '/'
    s.send(get_douyu_msg(join_group))

    while True:
        try:
            recv_data_str = get_next_data(s)
            if not parse_danmu_data(recv_data_str):
                get_danmu(room_id, group_id)
        except:
            print('some exception occurs, re-login')
            get_danmu(room_id, group_id)
            return

def get_next_data(socket):
    data_len_bytes = socket.recv(4)
    data_len = int.from_bytes(data_len_bytes, byteorder='little')
    data = socket.recv(data_len)
    #print(data)
    recv_data_str = data[8:-1].decode()
    return recv_data_str

def login_danmu_auth_server(address):
    devid_str = str(uuid.uuid4()).replace("-", "")
    time_str = str(int(time.time()))
    vk_md5_str = hashlib.md5(bytes(time_str + '7oE9nPEG9xXV69phU31FYCLUagKeYtsF' + devid_str, 'utf-8')).hexdigest()
    login_data = 'type@=loginreq/username@=qq_3HybyZDK/ct@=0/password@=/roomid@=' + roomt_id + '/devid@='\
    + devid_str + '/rt@=' + time_str + '/vk@=' + vk_md5_str + '/ver@=20150929/aver@=2016080605/ltkid@=58773771/biz@=1/stk@=f5e1c5abe2317df6/'

    msg = get_douyu_msg(login_data)

    print(msg)

    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect(address)
    s.sendall(msg)
    recv_data_str = get_next_data(s)
    matches = re.search('/userid@=(.*?)/.*/sessionid@=(.*?)/', recv_data_str).groups()
    if matches != None:
        uid = matches[0]
        sessionid = matches[1]
   
        recv_data_str = get_next_data(s)
        while 'type@=setmsggroup' not in recv_data_str:
            recv_data_str = get_next_data(s)

        gid = re.search('/gid@=(\d+)/', recv_data_str).group(1)

        send_data = 'type@=qrl/rid@=' + roomt_id + '/et@=0/'
        s.sendall(get_douyu_msg(send_data))
        send_data = 'type@=qtlnq/'
        s.sendall(get_douyu_msg(send_data))
        send_data = 'type@=qtlq/'
        s.sendall(get_douyu_msg(send_data))
        send_data = 'type@=reqog/uid@=' + uid
        s.sendall(get_douyu_msg(send_data))
        time_str = str(int(time.time()))
        send_data = 'type@=keeplive/tick@='+ time_str + '/vbw@=0/k@=4d162083032710d7c69c60c7966e608b/'
        s.sendall(get_douyu_msg(send_data))


        send_data = 'type@=chatmessage/receiver@=0/content@=' + 'hello world' +'/scope@=/col@=0/'
        s.sendall(get_douyu_msg(send_data))

        return gid, uid, sessionid
    return None

def fetch_room_info(url):
    html = urllib.request.urlopen(url).read().decode()

    room_info_json = re.search('var\s\$ROOM\s=\s({.*});', html).group(1)

    auth_server_json = re.search('\$ROOM\.args\s=\s({.*});', html).group(1)

    json_object = None
    try:
        json_object = json.loads(auth_server_json)
    except ValueError as e:
        print(e)
        return False
    
    servers = urllib.parse.unquote(json_object['server_config'])
    servers_array = json.loads(servers)
    auth_server_ip = servers_array[0]['ip']
    auth_server_port = servers_array[0]['port']

    return auth_server_ip, auth_server_port

auth_info = login_danmu_auth_server(address)
def get_https_opener(cookie_jar):
    context = ssl._create_unverified_context()
    https_handler = urllib.request.HTTPSHandler(context = context)

    cookie_support = urllib.request.HTTPCookieProcessor(cookie_jar)

    opener = urllib.request.build_opener(cookie_support, https_handler)
    
    return opener

def login_douyu(user_name, password):
       
    login_result = None

    cookie_jar = None
    if os.path.exists(douyu_cookie_file):
        cookie_jar = http.cookiejar.MozillaCookieJar()
        cookie_jar.load(douyu_cookie_file)
        login_result = get_info_from_cookie_jar(cookie_jar)
        if login_result != None:
            return login_result
        
    cookie_jar = http.cookiejar.MozillaCookieJar(douyu_cookie_file)

    opener = get_https_opener(cookie_jar)

    # Get captcha
    captcha_id = str(int(time.time() * 1000))
    captch_url = passport_douyu_host_url + 'api/captcha?v=' + captcha_id
    captcha_request = urllib.request.Request(captch_url, headers = headers)
    response = opener.open(captcha_request)
    captcha_code = input('captcha code:')

    md5_password = hashlib.md5(password.encode('utf-8')).hexdigest()
    params = urllib.parse.urlencode({'username': user_name, 
                            'password': md5_password, 
                            'login_type': 'nickname',
                            'client_id': 1,
                            'captcha_word': captcha_code,
                            't': int(time.time() * 1000)
                            })
    login_url = passport_douyu_host_url + 'iframe/login?' + params
    
    login_request = urllib.request.Request(login_url, headers = headers)
    response = opener.open(login_request).read().decode()
    json_resonse = response.strip('()')
    response_dict = json.loads(json_resonse)
    if response_dict['error'] == 0:
        code = response_dict['data']['code']
        uid = response_dict['data']['uid']

        params = urllib.parse.urlencode({'code': code,
                                         'uid' : uid,
                                         'client_id': 1
                                        })

        auth_url = douyu_host_url + 'api/passport/login?' + params
        auth_request = urllib.request.Request(auth_url, headers=headers)
        response = opener.open(auth_request).read().decode()
        cookie_jar.save(ignore_discard=True, ignore_expires=True)
        login_result = get_info_from_cookie_jar(cookie_jar)

    return login_result

def get_info_from_cookie_jar(cookie_jar):
    info = {}
    for cookie in cookie_jar:
        if 'acf_username' == cookie.name:
            info['user_name'] = cookie.value
        if 'acf_uid' == cookie.name:
            info['uid'] = cookie.value
        if 'acf_devid' == cookie.name:
            info['devid'] = cookie.value
        if 'acf_nickname' == cookie.name:
            info['nick_name'] = cookie.value
    if len(info) == 0:
        return None
    return info

user_name = input('user name:')
password = input('password:')

login_result = login_douyu(user_name, password)

#target_url = douyu_host_url + roomt_id
#auth_server_ip, auth_server_port = fetch_room_info(target_url)
#address = (auth_server_ip, int(auth_server_port))
#auth_info = login_danmu_auth_server(address)

#group_id = auth_info[0]
#get_danmu_thread = threading.Thread(target=get_danmu, args=(roomt_id,group_id))
#get_danmu_thread.start()
#get_danmu_thread.join()

