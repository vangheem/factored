import time
from datetime import datetime
import base64
import struct
import hmac
import hashlib

import random
try:
    random = random.SystemRandom()
    using_sysrandom = True
except NotImplementedError:
    using_sysrandom = False

from hashlib import sha256 as sha


# generated when process started, hard to guess
SECRET = random.randint(0, 1000000)


def get_random_string(length=12,
                      allowed_chars='abcdefghijklmnopqrstuvwxyz'
                                    'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789'):
    """
    Returns a securely generated random string.

    The default length of 12 with the a-z, A-Z, 0-9 character set returns
    a 71-bit value. log_2((26+26+10)^12) =~ 71 bits
    """
    if not using_sysrandom:
        # This is ugly, and a hack, but it makes things better than
        # the alternative of predictability. This re-seeds the PRNG
        # using a value that is hard for an attacker to predict, every
        # time a random string is required. This may change the
        # properties of the chosen random sequence slightly, but this
        # is better than absolute predictability.
        random.seed(
            sha(
                "%s%s%s" % (
                    random.getstate(),
                    time.time(),
                    SECRET)
                ).digest())
    return ''.join([random.choice(allowed_chars) for i in range(length)])


def generate_random_google_code(length=10):
    return base64.b32encode(get_random_string(length))


def make_random_code(length=255):
    return hashlib.sha1(hashlib.sha1(str(get_random_string(length))).
        hexdigest()[:5] + str(datetime.now().microsecond)).hexdigest()[:length]


def get_barcode_image(username, secretkey, appname):
    url = "https://www.google.com/chart"
    url += "?chs=200x200&chld=M|0&cht=qr&chl=otpauth://totp/"
    username = username + '--' + appname
    url += username + "%3Fsecret%3D" + secretkey
    return url


def get_google_auth_code(secretkey, tm=None):
    if tm is None:
        tm = int(time.time() / 30)
    secretkey = base64.b32decode(secretkey)
    # convert timestamp to raw bytes
    b = struct.pack(">q", tm)

    # generate HMAC-SHA1 from timestamp based on secret key
    hm = hmac.HMAC(secretkey, b, hashlib.sha1).digest()

    # extract 4 bytes from digest based on LSB
    offset = ord(hm[-1]) & 0x0F
    truncatedHash = hm[offset:offset + 4]

    # get the code from it
    code = struct.unpack(">L", truncatedHash)[0]
    code &= 0x7FFFFFFF
    code %= 1000000
    return "%06d" % code


def create_user(username):
    from factored.models import DBSession, User
    secret = generate_random_google_code()
    user = User(username=username, secret=secret)
    DBSession.add(user)
    return user


class CombinedDict(object):
    def __init__(self, *args):
        self.dicts = args

    def __getitem__(self, name):
        """
        need to handle nested dictionaries also
        """
        founddicts = []
        for dic in self.dicts:
            if name in dic:
                val = dic[name]
                if type(val) == dict:
                    founddicts.append(val)
                else:
                    return val
        if founddicts:
            return CombinedDict(*founddicts)
        raise KeyError

    __getattr__ = __getitem__
