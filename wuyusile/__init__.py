import logging
__log__ = logging.getLogger(__name__)
__log__.info('开始初始化')
from .client.mingancihuiclient import dxdmgchClient
__log__.info('结束初始化')
#exit(0)
from .network import connection
from .tl.custom import Button
from .tl import patched as _  # import for its side-effects
from . import version, events, utils, errors, types, functions, custom

__version__ = version.__version__

__all__ = [
    'dxdmgchClient', 'Button',
    'types', 'functions', 'custom', 'errors',
    'events', 'utils', 'connection'
]

