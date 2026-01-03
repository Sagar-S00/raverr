"""
Rave API Library
A Python library for interacting with the Rave app API and WebSocket
"""

# Main exports
from .api import RaveAPIClient
from .websocket import RaveWebSocketClient
from .bot import RaveBot, BotManager

# Model exports
from .models import (
    User,
    Mesh,
    MeshState,
    Video,
    Queue,
    QueueItem,
    StateMessage,
    UserState,
    Vote,
)

# WebSocket exports
from .websocket import (
    ProtooRequest,
    ProtooNotification,
    ProtooResponse,
    ChatMessage,
    WebSocketMessage,
)

# Utils exports
from .utils import (
    get_video_id,
    vote_video,
    get_mesh_info,
    get_friendships,
    get_users_list,
    get_invited_meshes,
    leave_mesh,
    upload_media,
    set_default_api_client,
    get_default_api_client,
)

__version__ = "0.1.0"

__all__ = [
    # Main classes
    'RaveAPIClient',
    'RaveWebSocketClient',
    'RaveBot',
    'BotManager',
    # Models
    'User',
    'Mesh',
    'MeshState',
    'Video',
    'Queue',
    'QueueItem',
    'StateMessage',
    'UserState',
    'Vote',
    # WebSocket
    'ProtooRequest',
    'ProtooNotification',
    'ProtooResponse',
    'ChatMessage',
    'WebSocketMessage',
    # Utils
    'get_video_id',
    'vote_video',
    'get_mesh_info',
    'get_friendships',
    'get_users_list',
    'get_invited_meshes',
    'leave_mesh',
    'upload_media',
    'set_default_api_client',
    'get_default_api_client',
]

