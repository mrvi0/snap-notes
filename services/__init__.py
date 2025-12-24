"""
Модуль для бизнес-логики и сервисов.
"""
from .sync_manager import SyncManager, MarkdownLevel

try:
    from .google_keep_sync import GoogleKeepSync
    __all__ = ['SyncManager', 'MarkdownLevel', 'GoogleKeepSync']
except ImportError:
    __all__ = ['SyncManager', 'MarkdownLevel']

