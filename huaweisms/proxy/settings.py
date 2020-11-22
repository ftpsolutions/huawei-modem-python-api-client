
USERNAME = "admin"
PASSWORD = "abcd"
MODEM_HOST = "192.168.1.1"
# At a 8 second polling cycle, this is ~ a minute
ERROR_COUNTDOWN = 7

# Normally no need to change this
HTTP_SERVER_PORT = 8000

try:
    # Get overrides from local settings
    from huaweisms.proxy.local_settings import *
except ImportError:
    pass
