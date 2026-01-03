"""
User model for Rave API
"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class User:
    """User information model"""
    id: int
    displayName: Optional[str] = None
    handle: Optional[str] = None
    online: Optional[bool] = None
    
    @classmethod
    def from_dict(cls, data: dict):
        """Create User from dictionary"""
        return cls(
            id=data.get('id'),
            displayName=data.get('displayName'),
            handle=data.get('handle'),
            online=data.get('online')
        )
    
    def to_dict(self) -> dict:
        """Convert User to dictionary"""
        result = {'id': self.id}
        if self.displayName is not None:
            result['displayName'] = self.displayName
        if self.handle is not None:
            result['handle'] = self.handle
        if self.online is not None:
            result['online'] = self.online
        return result

