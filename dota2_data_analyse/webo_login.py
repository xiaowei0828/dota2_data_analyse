#coding=utf-8

import urllib.error
import urllib.request
import re
import rsa
import http.cookiejar
import base64
import json
import urllib
import urllib.parse
import binascii
import threading

cookie_file = 'cookie.txt'

class launcher():

    def __init__(self, username, password):
        self.password = password
        self.username = username
    
    def get_prelogin_args(self):

        '''
        该函数用于模拟预登陆过程，并获取服务器返回的 nonce， servertime, pub_key 等信息
        '''
        json_pattern = re.compile('\((.*)\)')
        url = 'http://login.sina.com.cn/sso/prelogin.php?entry=weibo&callback=sinaSSOController.preloginCallBack&su=&' + self.get_encrypted_name() + '&rsakt=mod&checkpin=1&client=ssologin.js(v1.4.18)'
        try:
            request = urllib.request.Request(url)
            response = urllib.request.urlopen(request)
            raw_data = response.read().decode('utf-8')
            json_data = json_pattern.search(raw_data).group(1)
            data = json.loads(json_data)
            return data
        except urllib.error.URLError as e:
            print(e)
            return None
        except json.JSONDecodeError as e:
            print(e)
            return None

    def get_encrypted_pw(self, data):
        rsa_e = 65537 #0x10001
        pw_string = str(data['servertime']) + '\t' + str(data['nonce']) + '\n' + str(self.password)
        key = rsa.PublicKey(int(data['pubkey'], 16), rsa_e)
        pw_encrypted = rsa.encrypt(pw_string.encode('utf-8'), key)
        self.password = '' #清空password
        passwd = binascii.b2a_hex(pw_encrypted)
        print(passwd)
        return passwd

    def get_encrypted_name(self):
        username_urllike = urllib.request.quote(self.username)
        username_encrypted = base64.b64encode(bytes(username_urllike, encoding = 'utf-8'))
        return username_encrypted.decode('utf-8')

    def enableCookies(self):

        #建立一个cookies容器
        cookie_container = http.cookiejar.MozillaCookieJar(cookie_file)
        #将一个cookies容器和一个HTTP的cookie的处理器绑定
        cookie_support = urllib.request.HTTPCookieProcessor(cookie_container)
        #创建一个opener，设置一个handler用于处理http的url打开
        opener = urllib.request.build_opener(cookie_support, urllib.request.HTTPHandler)
        #安装opener，次后调用urlopen()时会使用安装过的opener对象
        urllib.request.install_opener(opener)

        return cookie_container

    def build_post_data(self, raw):
        post_data = {
            "entry":"weibo",
            "gateway":"1",
            "from":"",
            "savestate":"7",
            "useticket":"1",
            "pagerefer":"http://passport.weibo.com/visitor/visitor?entry=miniblog&a=enter&url=http%3A%2F%2Fweibo.com%2F&domain=.weibo.com&ua=php-sso_sdk_client-0.6.14",
            "vsnf":"1",
            "su":self.get_encrypted_name(),
            "service":"miniblog",
            "servertime":raw['servertime'],
            "nonce":raw['nonce'],
            "pwencode":"rsa2",
            "rsakv":raw['rsakv'],
            "sp":self.get_encrypted_pw(raw),
            "sr":"1280*800",
            "encoding":"UTF-8",
            "prelt":"77",
            "url":"http://weibo.com/ajaxlogin.php?framelogin=1&callback=parent.sinaSSOController.feedBackUrlCallBack",
            "returntype":"META"
        }
        data = urllib.parse.urlencode(post_data).encode('utf-8')
        return data

    def login(self):
        url = 'http://login.sina.com.cn/sso/login.php?client=ssologin.js(v1.4.18)'
        cookie_container = self.enableCookies()
        data = self.get_prelogin_args()
        post_data = self.build_post_data(data)

        headers = {
            "User-Agent":"Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/49.0.2623.87 Safari/537.36"
            }

        try:
            request = urllib.request.Request(url=url, data=post_data,headers = headers)
            response = urllib.request.urlopen(request)
            html = response.read().decode('GBK')
        except urllib.error as e:
            print(e.code)

        p = re.compile('location\.replace\(\'(.*?)\'\)')
        p2 = re.compile(r'"userdomain":"(.*?)"')

        try:
            login_url = p.search(html).group(1)
            print(login_url)
            request = urllib.request.Request(login_url)
            response = urllib.request.urlopen(request)
            page = response.read().decode('utf-8')
            print(page)

            login_url = "http://weibo.com/" + p2.search(page).group(1)
            request = urllib.request.Request(login_url)
            response = urllib.request.urlopen(login_url)
            final = response.read().decode('utf-8')

            print("Login succeed!")

            cookie_container.save(ignore_discard=True, ignore_expires=True)
        except:
            print('Login error!')
            return 0

class GetFollows(threading.Thread):
    
    lock = threading.RLock()
    '''
    用来获取一页的关注者信息
    '''
    def __init__(self, page_num, follows_info_array):
        threading.Thread.__init__(self)
        self.page_num = page_num
        self.follows_info_array = follows_info_array

    def run(self):
        follows_url_prefix = 'http://weibo.com/1927698523/follow?'
        params = urllib.parse.urlencode(
        {'Pl_Official_RelationMyfollow__108_page': self.page_num})
        follows_url = follows_url_prefix + params
        request = urllib.request.Request(follows_url)
        response = opener.open(request)
        page = response.read().decode('utf-8')

        nick_pattern = re.compile('gid=.*?&nick=(.*?)&uid=(.*?)&')
        matches = nick_pattern.findall(page)
        file = open('page_data' + str(self.page_num), 'w')
        file.write(page)
        GetFollows.lock.acquire()
        for match in matches:
            self.follows_info_array.append(match)
        print("Thread " + str(self.page_num) + " count:" + str(len(matches)))
        GetFollows.lock.release()

#launcher = launcher('1243764818@qq.com', 'xiaowei19900828')

#launcher.login()
cookie = http.cookiejar.MozillaCookieJar()
cookie.load(cookie_file, ignore_discard=True, ignore_expires=True)
opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cookie))

home_url = 'http://weibo.com/u/1927698523/home'

request = urllib.request.Request(home_url)
response = opener.open(request)
page = response.read().decode('utf-8')

all_follows_pattern = re.compile('<strong node-type=\\\\"follow\\\\">(.*?)<\\\\/strong>')
all_follows_num = int(all_follows_pattern.findall(page)[0])

follows_pages = int(all_follows_num / 30)
remains = all_follows_num % 30
if remains != 0:
    follows_pages += 1

follows_info_array = []
thread_pool = []
for i in range(follows_pages):
    thread_pool.append(GetFollows((i+1), follows_info_array))

for i in range(len(thread_pool)):
    thread_pool[i].start()

for i in range(len(thread_pool)):
    thread_pool[i].join()

print("Total follows:" + str(len(follows_info_array)))
print(follows_info_array)
#print(page)