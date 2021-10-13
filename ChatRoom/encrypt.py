# -*- coding: utf-8 -*-
import rsa

class encrypt():

    def __init__(self):
        """ init """
        self.pubkey, self.privkey = rsa.newkeys(512)

        # 加密长度
        self.encrypt_len = 53
        # 解密长度
        self.rsaDecrypt_len = 64

    def _cut(self, obj, sec):

        return [obj[i:i+sec] for i in range(0,len(obj),sec)]

    def encrypt(self, info):

        crypto = b""
        for line in self._cut(info, self.encrypt_len):
            crypto += rsa.encrypt(line, self.pubkey)

        return crypto

    def encrypt_user(self, info, pubkey):

        crypto = b""
        for line in self._cut(info, self.encrypt_len):
            crypto += rsa.encrypt(line, pubkey)

        return crypto

    def rsaDecrypt(self, info):

        content = b""
        for line in self._cut(info, self.rsaDecrypt_len):
            content += rsa.decrypt(line, self.privkey)

        return content
