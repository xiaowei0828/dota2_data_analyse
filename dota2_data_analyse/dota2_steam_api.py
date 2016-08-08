
from steam import SteamClient
from dota2 import Dota2Client
import logging

user_name = "chpeui0828"

user_password = "weirongbin1990"

logging.basicConfig(format='[%(asctime)s] %(levelname)s %(name)s: %(message)s', level=logging.DEBUG)

client = SteamClient()
dota = Dota2Client(client)

login_called = False

@client.on('connected')
def login():
    global login_called
    if not login_called:
        client.login(user_name, user_password)
        login_called = True

@client.on(client.EVENT_AUTH_CODE_REQUIRED)
def auth_code_prompt(is_2fa, code_mismatch):
    if is_2fa:
        code = input("Enter 2FA Code: ")
        client.login(user_name, user_password, two_factor_code=code)
    else:
        code = input("Enter Email Code: ")
        client.login(user_name, user_password, auth_code=code)

@client.on('logged_on')
def start_dota():
    dota.launch()

client.connect()
client.run_forever()