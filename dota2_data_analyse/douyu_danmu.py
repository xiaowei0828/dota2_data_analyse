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

class LoginClient:
    '''
    Used to login douyu and get some login info
    '''
    __headers = { 'User-Agent' : 'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/49.0.2623.87 Safari/537.36'}
    __douyu_cookie_file = 'douyu_cookie'
    __douyu_host_url = 'http://www.douyu.com/'
    __passport_douyu_host_url = 'https://passport.douyu.com/'

    def __init__(self, user_name, password):
        self.__user_name = user_name
        self.__password = password
        self.__login_info = None
        self.__room_info_dict = {}
        if os.path.exists(LoginClient.__douyu_cookie_file):
            self.__cookie_jar = http.cookiejar.MozillaCookieJar()
            self.__cookie_jar.load(LoginClient.__douyu_cookie_file)
        else:
            self.__cookie_jar = http.cookiejar.MozillaCookieJar(LoginClient.__douyu_cookie_file)

        self.__https_opener = self.__get_https_opener()

        self.__http_opener = self.__get_http_opener()

    def __get_https_opener(self):
        context = ssl._create_unverified_context()
        https_handler = urllib.request.HTTPSHandler(context = context)

        cookie_support = urllib.request.HTTPCookieProcessor(self.__cookie_jar)

        opener = urllib.request.build_opener(cookie_support, https_handler)
    
        return opener

    def __get_http_opener(self):

        cookie_support = urllib.request.HTTPCookieProcessor(self.__cookie_jar)

        opener = urllib.request.build_opener(cookie_support, urllib.request.HTTPHandler)
    
        return opener

    def __is_login_cookie_valid(self):
        # Test if the saved cookies is valid
        profile_url = LoginClient.__douyu_host_url + 'member'
        response = self.__http_opener.open(profile_url).read().decode()
        match = re.search('<title>(.*?)</title>', response)
        if match and '个人中心' in match.group(1):
            return True
        return False

    def __login_douyu_real(self):
        captcha_id = str(int(time.time() * 1000))
        captch_url = LoginClient.__passport_douyu_host_url + 'api/captcha?v=' + captcha_id
        captcha_request = urllib.request.Request(captch_url, headers = LoginClient.__headers)
        response = self.__https_opener.open(captcha_request)
        captcha_code = input('captcha code:')

        md5_password = hashlib.md5(self.__password.encode('utf-8')).hexdigest()
        params = urllib.parse.urlencode({'username': self.__user_name, 
                                'password': md5_password, 
                                'login_type': 'nickname',
                                'client_id': 1,
                                'captcha_word': captcha_code,
                                't': int(time.time() * 1000)
                                })
        login_url = LoginClient.__passport_douyu_host_url + 'iframe/login?' + params
    
        login_request = urllib.request.Request(login_url, headers = LoginClient.__headers)
        response = self.__https_opener.open(login_request).read().decode()
        json_resonse = response.strip('()')
        response_dict = json.loads(json_resonse)
        if response_dict['error'] == 1:
            # 验证码错误
            print('Captcha code is error')
            return self.__login_douyu_real()
        elif response_dict['error'] == 0:
            code = response_dict['data']['code']
            uid = response_dict['data']['uid']

            params = urllib.parse.urlencode({'code': code,
                                                'uid' : uid,
                                                'client_id': 1
                                            })

            auth_url = LoginClient.__douyu_host_url + 'api/passport/login?' + params
            auth_request = urllib.request.Request(auth_url, headers= LoginClient.__headers)
            response = self.__https_opener.open(auth_request).read().decode()
            return True

    def login_douyu(self):
            
        if self.__is_login_cookie_valid():
            # No need to login
            self.__login_info ={cookie.name : cookie.value for cookie in self.__cookie_jar}
            return True
        elif self.__login_douyu_real():
            # Get captcha
            self.__cookie_jar.save(ignore_discard=True, ignore_expires=True)
            self.__login_info = {cookie.name : cookie.value for cookie in self.__cookie_jar}
            return True

        return False

    def get_login_info(self):
        return self.__login_info

    def get_room_info(self, room_id):
        if room_id in self.__room_info_dict:
            return self.__room_info_dict[room_id]

        room_info = {}

        url = LoginClient.__douyu_host_url + room_id
        html = self.__http_opener.open(url).read().decode()

        match = re.search('var\s\$ROOM\s=\s({.*});', html)
        if match != None:
            room_info_json = match.group(1)
            room_info_dict = json.loads(room_info_json)
            room_info['room_info'] = room_info_dict

        match = re.search('\$ROOM\.args\s=\s({.*});', html)
        if match != None:
            auth_server_json = match.group(1)
            auth_server_dict = json.loads(auth_server_json)
            auth_server_list = json.loads(urllib.parse.unquote(auth_server_dict['server_config']))
            room_info['auth_server_list'] = auth_server_list

        gift_infos = re.findall('data-type="gift"[^>]*>', html, re.M)
        gift_info_dict = {}
        for gift_info in gift_infos:
            matches = re.findall('([^=\s]*)="([^"]*)"', gift_info)
            gift_info = {}
            gift_id = str()
            for match in matches:
                if match[0] == 'data-giftid':
                    gift_id = match[1]
                else:
                    gift_info[match[0]] = match[1]
            gift_info_dict[gift_id] = gift_info
        if len(gift_info_dict) != 0:
            room_info['gift_info'] = gift_info_dict
        self.__room_info_dict[room_id] = room_info
        return room_info

class DanmuClient:

    __address_danmu_1 = ('danmu.douyutv.com', 8601)
    __address_danmu_2 = ('danmu.douyutv.com', 8602)
    __address_danmu_3 = ('danmu.douyutv.com', 12601)
    __address_danmu_4 = ('danmu.douyutv.com', 12602)

    def __init__(self, user_name, password, room_id):
        self.__douyu_login_client = LoginClient(user_name, password)
        self.__user_name = user_name
        self.__password = password
        self.__room_id = room_id
        self.__room_info = None
        self.__recv_danmu_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.__auth_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        self.__recv_msg_pattern = re.compile('((?:(?!@).)*)@=((?:(?!/).)*)/')

        self.__gid = None
        self.__uid = None
        self.__sessionid = None

    def __get_next_data(self, socket):
        try:
            data_len_bytes = socket.recv(4)
            recv_len = len(data_len_bytes)
            while recv_len < 4:
                left_len = 4 - recv_len
                data_len_bytes += socket.recv(left_len)
                recv_len = len(data_len_bytes)

            data_len = int.from_bytes(data_len_bytes, byteorder='little')
            data = socket.recv(data_len)
            recv_len = len(data)
            while recv_len < data_len:
                left_len = data_len - recv_len
                data += socket.recv(left_len)
                recv_len = len(data)
            #print(data)
            recv_data_str = data[8:-1].decode()
            return recv_data_str
        except os.error as e:
            print(e)
        except UnicodeDecodeError as e:
            print(e)

    def __wrap_danmu_msg(self, content):
        length = bytearray([len(content) + 10, 0x00, 0x00, 0x00])
        code = length
        magic = bytearray([0xb1, 0x02, 0x00, 0x00])
        end = b'/\x00'
        return length + code + magic + bytes(content.encode('utf-8')) + end

    def __send_msg(self, msg, socket):
        data = self.__wrap_danmu_msg(msg)
        try:
            socket.sendall(data)
        except os.error as e:
            print(e)

    def __parse_recv_msg(self, data_str):
        matches = self.__recv_msg_pattern.findall(data_str)
        if matches != None:
            parse_result = {}
            for match in matches:
                parse_result[match[0]] = match[1]
            return parse_result
        return None

    def __auth_socket_keep_alive(self):
        while True:
            time_str = str(int(time.time()))
            data = 'type@=keeplive/tick@='+ time_str
            self.__send_msg(data, self.__auth_socket)
            time.sleep(45)

    def __recv_socket_keep_alive(self):
        while True:
            data = 'type@=mrkl'
            self.__send_msg(data, self.__recv_danmu_socket)
            time.sleep(45)

    def __process_mrkl(self, danmu):
        pass

    def __process_chat_msg(self, danmu):
        pass

    def login_danmu_auth_server(self):
        # First login douyu to get some msg
        if self.__douyu_login_client.login_douyu() == False:
            print('Login douyu web server failed')
            return False

        login_info = self.__douyu_login_client.get_login_info()
        self.__room_info = self.__douyu_login_client.get_room_info(self.__room_id)
        
        # Select an auth server
        if 'auth_server_list' not in self.__room_info:
            print('Get auth server failed')

        auth_server = (self.__room_info['auth_server_list'][0]['ip'], int(self.__room_info['auth_server_list'][0]['port']))

        self.__auth_socket.connect(auth_server)

        time_str = str(int(time.time()))
        vk_md5_str = hashlib.md5(bytes(time_str + '7oE9nPEG9xXV69phU31FYCLUagKeYtsF' + login_info['acf_devid'], 'utf-8')).hexdigest()
        password_md5 = hashlib.md5(bytes(self.__password, 'utf-8')).hexdigest()
        login_data = 'type@=loginreq/username@=' + login_info['acf_username'] + '/ct@=' + login_info['acf_ct'] +\
                        '/password@=' + '/roomid@=' + self.__room_id + '/devid@=' + login_info['acf_devid'] + '/rt@=' + time_str +\
                        '/vk@=' + vk_md5_str + '/ver@=20150929/aver@=2016080605' + '/ltkid@=' + login_info['acf_ltkid'] +\
                        '/biz@=' + login_info['acf_biz'] + '/stk@=' + login_info['acf_stk']
        self.__send_msg(login_data, self.__auth_socket)

        recv_data_str = self.__get_next_data(self.__auth_socket)
        parse_result = self.__parse_recv_msg(recv_data_str)

        if 'type' in parse_result and parse_result['type'] == 'loginres':
            self.__uid = parse_result['userid']
            self.__sessionid = parse_result['sessionid']
   
            recv_data_str = self.__get_next_data(self.__auth_socket)
            while 'type@=setmsggroup' not in recv_data_str:
                recv_data_str = self.__get_next_data(self.__auth_socket)

            parse_result = self.__parse_recv_msg(recv_data_str)
            self.__gid = parse_result['gid']

            threading._start_new_thread(self.__auth_socket_keep_alive, ())
            return True

        return False

    def login_danmu_server(self, is_all_danmu = False):

        if self.__gid == None:
            if not self.login_danmu_auth_server():
                print('Login danmu auth server failed')
                return False

        login_info = self.__douyu_login_client.get_login_info()

        self.__recv_danmu_socket.connect(danmu_client.__address_danmu_1)

        login_data = 'type@=loginreq/username@=' + login_info['acf_username'] + '/password@=1234567890123456/roomid@=' + self.__room_id

        self.__send_msg(login_data, self.__recv_danmu_socket)

        recv_data = self.__get_next_data(self.__recv_danmu_socket)
        parse_result = self.__parse_recv_msg(recv_data)
        if 'type' in parse_result and parse_result['type'] == 'loginres':
            if is_all_danmu:
                join_group = 'type@=joingroup/rid@=' + self.__room_id + '/gid@=' + '-9999'
            else:
                join_group = 'type@=joingroup/rid@=' + self.__room_id + '/gid@=' + self.__gid

            self.__send_msg(join_group, self.__recv_danmu_socket)
            threading._start_new_thread(self.__recv_socket_keep_alive, ())

    def get_one_danmu(self):
        recv_data_str = self.__get_next_data(self.__recv_danmu_socket)
        return self.__parse_recv_msg(recv_data_str)

    def send_one_danmu(self, msg):
        data = 'type@=chatmessage/receiver@=0/content@=' + msg +'/scope@=/col@=0'
        self.__send_msg(data, self.__auth_socket)

    def parse_danmu(self, danmu):
        if 'type' in danmu:

            function_name = '__process_' + danmu['type']
            call_function = function_name + '(self, danmu)'
            eval(call_function)

            if danmu['type'] == 'chatmsg':
                try:
                    print(danmu['nn'] + ' : ' + danmu['txt'])
                except:
                    print('meet some special characters')
            elif danmu['type'] == 'uenter':
                print(danmu['nn'] + '(level ' + str(danmu['level'] + ') 进入了房间'))
            elif danmu['type'] == 'onlinegift':
                print(danmu['nn'] + '领取了' + danmu['sil'] + '个鱼丸')
            elif danmu['type'] == 'dgb':
                if self.__room_info == None:
                    self.__room_info = self.__douyu_login_client.get_room_info()
                gitf_info_dict = self.__room_info['gift_info']
                print(danmu['nn'] + '赠送了 ' + gitf_info_dict[danmu['gfid']]['data-giftname'])
            elif danmu['type'] == 'ssd':
                print(danmu['content'])
            elif danmu['type'] == 'spbc':
                print(danmu['sn'] + '赠送给' + danmu['dn'] + ' ' + danmu['gc'] + 'x' + danmu['gn'])
            elif danmu['type'] == 'newblackres':
                print(danmu['dnic'] + ' 被 ' + danmu['snic'] + ' 禁言到' + time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(danmu['endtime'])))
            elif danmu['type'] == 'rankup':
                rank_name = str()
                if danmu['rkt'] == 1:
                    rank_name = '周榜'
                elif danmu['rkt'] == 2:
                    rank_name = '总榜'
                elif danmu['rkt'] == 4:
                    rank_name = '日榜'

                print(danmu['nk'] + ' 在' + rank_name + '中的排名提升到了' + danmu['rn'])
            elif danmu['type'] == 'bc_buy_deserve':
                chouqin_name = str()
                if danmu['lev'] == 1:
                    chouqin_name = '初级酬勤'
                elif danmu['lev'] == 2:
                    chouqin_name = '中级酬勤'
                elif danmu['lev'] == 3:
                    chouqin_name = '高级酬勤'
            else:
                print(danmu)
        else:
            print(danmu)


if __name__ == '__main__':
    room_id = '52876'
    user_name = 'xiaaowei'#input('user name:')
    password = 'chpeui1990'#input('password:')

    danmu_client = DanmuClient(user_name, password, room_id)
    result = danmu_client.login_danmu_server()
    while True:
        #msg = input('message:')
        #danmu_client.send_one_danmu(msg)
        danmu = danmu_client.get_one_danmu()
        danmu_client.parse_danmu(danmu)

