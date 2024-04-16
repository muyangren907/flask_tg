"""
This package defines clients as subclasses of others, and then a single
`flask.client.mingancihuiclient.dxdmgchClient` which is subclass of them
all to provide the final unified interface while the methods can live in
different subclasses to be more maintainable.

The ABC is `flask.client.mingancihuibaseclient.dxdmgchBaseClient` and the
first implementor is `flask.client.users.UserMethods`, since calling
requests require them to be resolved first, and that requires accessing
entities (users).
"""
import logging
__log__ = logging.getLogger(__name__)
# __log__.info('开始初始化 客户端')
from .mingancihuibaseclient import dxdmgchBaseClient
# __log__.info('结束初始化 客户端')
#exit(0)
from .users import UserMethods  # Required for everything
from .messageparse import MessageParseMethods  # Required for messages
from .uploads import UploadMethods  # Required for messages to send files
from .updates import UpdateMethods  # Required for buttons (register callbacks)
from .buttons import ButtonMethods  # Required for messages to use buttons
from .messages import MessageMethods
from .chats import ChatMethods
from .dialogs import DialogMethods
from .downloads import DownloadMethods
from .account import AccountMethods
from .auth import AuthMethods
from .bots import BotMethods
from .mingancihuiclient import dxdmgchClient
