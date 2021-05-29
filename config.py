# https://core.telegram.org/api/obtaining_api_id
# get your telegram API ID and API hash here
# replace 123456 with your API id
# replace your_hash with your own value
API_ID = 123456
API_HASH = 'your hash'

# Set SOCKS5 proxy
# example with tor proxy:
# PROXY_HOST = '127.0.0.1'
# PROXY_PORT = 9050
PROXY_HOST = ''
PROXY_PORT = 0

# enable debug mode
DEBUG = False

# List of disabled modules.
# Modules specified here will not be loaded at startup.
# IGNORE = ['tesseract', 'youdl', 'curl', ...], see ./core/modules for file names
IGNORE = [
    'tesseract',
    'vkdl',
    'evaluate',
]

# +---------------------------------------------------------+
# +-------------+
# | VK API      |
# +-------------+
# To enable this module remove vkdl from IGNORE list above.
# Provide email (or phone number, only digits) with password
# to access VK API.
# https://github.com/python273/vk_api
VK_LOGIN = ''
VK_PASS = ''

# delete folders with music after upload
DELETE_AFTER_UPLOAD = True
# +---------------------------------------------------------+


# +---------------------------------------------------------+
# +-------------+
# | OPENWEATHER |
# +-------------+
# https://openweathermap.org/appid
# get OWM API key ^^^^^^^^^^
# replace api_key with your own value
OWM = 'api key'
# +---------------------------------------------------------+


# +---------------------------------------------------------+
# +-------------+
# | YOUTUBE-DL  |
# +-------------+
# If you do not have a server to host, leave SERVER_PATH and URL as they are.
# If SERVER_PATH and URL are not specified, bot will upload the video directly.
# ----------------------------------
# path to your server data directory
# EXAMPLE: "/var/www/html/temp"
SERVER_PATH = None
# ----------------------------------
# apply URL to this data directory
# EXAMPLE: "https://website.com/temp"
URL = None
# so you can provide a direct link to the downloaded file.
# make sure bot has rights to access directory provided 
# (not owned by www-data or shares rights with it)
# +---------------------------------------------------------+


# +---------------------------------------------------------+
# start of your command, i.e !command
# can be '/' as well: /command
S = '!'
# how your commands will look like, i.e !ping@moe
CALL_NAME = "@moe"

# If user media is tracked, reduce quality of saved PNGs to 70%
OPT_PNG = True
# convert saved .WEBP files to .PNG
CONV = True
# +---------------------------------------------------------+


# +---------------------------------------------------------+
# Drop saved media to SFTP server
SFTP_ENABLED = False
SFTP_HOST = '192.168.0.101'
SFTP_KEY = '/home/bot/.ssh/id_rsa'
# ^^^ path to your local private key
SFTP_USR = 'bot'
# ^^^ SFTP remote username
SFTP_PORT = 22
SFTP_DIR = 'files'
# ^^^ SFTP remote upload directory
# +---------------------------------------------------------+


# ping replies, add whatever you want
PING = ["Yes.", "No", 
        "Pong", "(╯°□°)╯︵ ┻━┻"]
