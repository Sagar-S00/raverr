"""
WebSocket message models
"""

from dataclasses import dataclass
from typing import Optional, Dict, Any, List
from ..models.state import StateMessage
from ..models.queue import Queue


@dataclass
class ChatMessage:
    """Chat message model"""
    chat: str
    id: str
    from_: Optional[str] = None
    reply: Optional[str] = None
    detected_lang: Optional[str] = None
    translations: Optional[Dict[str, str]] = None
    userId: Optional[str] = None
    media: Optional[List[Dict[str, Any]]] = None
    
    @classmethod
    def from_dict(cls, data: dict):
        """Create ChatMessage from dictionary"""
        return cls(
            chat=data.get('chat', ''),
            id=data.get('id', ''),
            from_=data.get('from'),
            reply=data.get('reply'),
            detected_lang=data.get('detected_lang'),
            translations=data.get('translations'),
            userId=data.get('userId'),
            media=data.get('media')
        )
    
    def to_dict(self) -> dict:
        """Convert ChatMessage to dictionary"""
        result = {
            'chat': self.chat,
            'id': self.id
        }
        if self.from_ is not None:
            result['from'] = self.from_
        if self.reply is not None:
            result['reply'] = self.reply
        if self.detected_lang is not None:
            result['detected_lang'] = self.detected_lang
        if self.translations is not None:
            result['translations'] = self.translations
        if self.userId is not None:
            result['userId'] = self.userId
        if self.media is not None:
            result['media'] = self.media
        return result


@dataclass
class WebSocketMessage:
    """Base WebSocket message wrapper"""
    notification: Optional[bool] = None
    response: Optional[bool] = None
    request: Optional[bool] = None
    method: Optional[str] = None
    data: Optional[Dict[str, Any]] = None
    id: Optional[int] = None
    ok: Optional[bool] = None
    
    @classmethod
    def from_dict(cls, data: dict):
        """Create WebSocketMessage from dictionary"""
        return cls(
            notification=data.get('notification'),
            response=data.get('response'),
            request=data.get('request'),
            method=data.get('method'),
            data=data.get('data'),
            id=data.get('id'),
            ok=data.get('ok')
        )
    
    def to_dict(self) -> dict:
        """Convert WebSocketMessage to dictionary"""
        result = {}
        if self.notification is not None:
            result['notification'] = self.notification
        if self.response is not None:
            result['response'] = self.response
        if self.request is not None:
            result['request'] = self.request
        if self.method is not None:
            result['method'] = self.method
        if self.data is not None:
            result['data'] = self.data
        if self.id is not None:
            result['id'] = self.id
        if self.ok is not None:
            result['ok'] = self.ok
        return result
    
    def is_notification(self) -> bool:
        """Check if this is a notification"""
        return self.notification is True
    
    def is_response(self) -> bool:
        """Check if this is a response"""
        return self.response is True
    
    def is_request(self) -> bool:
        """Check if this is a request"""
        return self.request is True
    
    def get_state_message(self) -> Optional[StateMessage]:
        """Extract StateMessage if this is a stateMessage notification"""
        if self.is_notification() and self.method == 'stateMessage' and self.data:
            message_str = self.data.get('message', '')
            if message_str:
                import json
                try:
                    state_data = json.loads(message_str)
                    return StateMessage.from_dict(state_data)
                except (json.JSONDecodeError, Exception):
                    pass
        return None
    
    def get_queue_message(self) -> Optional[Queue]:
        """Extract Queue if this is a queueMessage notification"""
        if self.is_notification() and self.method == 'queueMessage' and self.data:
            message_str = self.data.get('message', '')
            if message_str:
                import json
                try:
                    queue_data = json.loads(message_str)
                    return Queue.from_dict(queue_data)
                except (json.JSONDecodeError, Exception):
                    pass
        return None
    
    def get_chat_message(self) -> Optional[ChatMessage]:
        """Extract ChatMessage if this is a chatMessage notification"""
        if self.is_notification() and self.method == 'chatMessage' and self.data:
            return ChatMessage.from_dict(self.data)
        return None

