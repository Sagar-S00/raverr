"""
Mesh/Room model for Rave API
"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class Mesh:
    """Mesh/Room information model"""
    id: str
    server: Optional[str] = None
    room_id: Optional[str] = None
    privacy_mode: Optional[str] = None
    play_mode: Optional[str] = None
    voip_mode: Optional[str] = None
    maturity: Optional[str] = None
    
    @classmethod
    def from_dict(cls, data: dict):
        """Create Mesh from dictionary"""
        return cls(
            id=data.get('id', ''),
            server=data.get('server'),
            room_id=data.get('id'),  # room_id is often the same as id
            privacy_mode=data.get('privacy_mode'),
            play_mode=data.get('play_mode'),
            voip_mode=data.get('voip_mode'),
            maturity=data.get('maturity')
        )
    
    def to_dict(self) -> dict:
        """Convert Mesh to dictionary"""
        result = {'id': self.id}
        if self.server is not None:
            result['server'] = self.server
        if self.room_id is not None:
            result['room_id'] = self.room_id
        if self.privacy_mode is not None:
            result['privacy_mode'] = self.privacy_mode
        if self.play_mode is not None:
            result['play_mode'] = self.play_mode
        if self.voip_mode is not None:
            result['voip_mode'] = self.voip_mode
        if self.maturity is not None:
            result['maturity'] = self.maturity
        return result


@dataclass
class MeshState:
    """Mesh state information from state messages"""
    url: Optional[str] = None
    video_url: Optional[str] = None
    video_instance_id: Optional[str] = None
    status: Optional[str] = None
    server: Optional[str] = None
    time: Optional[float] = None
    position: Optional[float] = None
    privacy_mode: Optional[str] = None
    play_mode: Optional[str] = None
    voip_mode: Optional[str] = None
    maturity: Optional[str] = None
    
    @classmethod
    def from_dict(cls, data: dict):
        """Create MeshState from dictionary"""
        return cls(
            url=data.get('url'),
            video_url=data.get('video_url'),
            video_instance_id=data.get('video_instance_id'),
            status=data.get('status'),
            server=data.get('server'),
            time=data.get('time'),
            position=data.get('position'),
            privacy_mode=data.get('privacy_mode'),
            play_mode=data.get('play_mode'),
            voip_mode=data.get('voip_mode'),
            maturity=data.get('maturity')
        )
    
    def to_dict(self) -> dict:
        """Convert MeshState to dictionary"""
        result = {}
        if self.url is not None:
            result['url'] = self.url
        if self.video_url is not None:
            result['video_url'] = self.video_url
        if self.video_instance_id is not None:
            result['video_instance_id'] = self.video_instance_id
        if self.status is not None:
            result['status'] = self.status
        if self.server is not None:
            result['server'] = self.server
        if self.time is not None:
            result['time'] = self.time
        if self.position is not None:
            result['position'] = self.position
        if self.privacy_mode is not None:
            result['privacy_mode'] = self.privacy_mode
        if self.play_mode is not None:
            result['play_mode'] = self.play_mode
        if self.voip_mode is not None:
            result['voip_mode'] = self.voip_mode
        if self.maturity is not None:
            result['maturity'] = self.maturity
        return result

