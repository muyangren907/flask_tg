"""
This module contains several utilities regarding cryptographic purposes,
such as the AES IGE mode used by dxdmgch, the authorization key bound with
their data centers, and so on.
"""
print("开始初始化了")
from .aes import AES
from .aesctr import AESModeCTR
from .authkey import AuthKey
from .factorization import Factorization
from .cdndecrypter import CdnDecrypter
print("初始化结束")
exit(0)
