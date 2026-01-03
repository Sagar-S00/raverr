"""
Protoo protocol message classes
"""

import json
import time
from typing import Dict, Any, Optional


class ProtooRequest:
    """Protoo protocol request message"""
    
    def __init__(self, method: str, data: Dict[str, Any], request_id: Optional[int] = None):
        self.request = True
        self.method = method
        self.id = request_id if request_id is not None else int(time.time() * 1000) % 1000000
        self.data = data
    
    def to_dict(self) -> Dict[str, Any]:
        # Match the order from websocket history: data, id, method, request
        return {
            "data": self.data,
            "id": self.id,
            "method": self.method,
            "request": self.request
        }
    
    def to_json(self) -> str:
        return json.dumps(self.to_dict())


class ProtooNotification:
    """Protoo protocol notification message"""
    
    def __init__(self, method: str, data: Dict[str, Any]):
        self.notification = True
        self.method = method
        self.data = data
    
    def to_dict(self) -> Dict[str, Any]:
        # Match the order from websocket history: data, method, notification
        return {
            "data": self.data,
            "method": self.method,
            "notification": self.notification
        }
    
    def to_json(self) -> str:
        return json.dumps(self.to_dict())


class ProtooResponse:
    """Protoo protocol response message"""
    
    def __init__(self, response_id: int, ok: bool, data: Optional[Dict[str, Any]] = None):
        self.response = True
        self.id = response_id
        self.ok = ok
        self.data = data or {}
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]):
        """Create ProtooResponse from dictionary"""
        return cls(
            response_id=data.get('id'),
            ok=data.get('ok', False),
            data=data.get('data', {})
        )
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "response": self.response,
            "id": self.id,
            "ok": self.ok,
            "data": self.data
        }
    
    def to_json(self) -> str:
        return json.dumps(self.to_dict())

