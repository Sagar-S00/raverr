"""
State message models for Rave API
"""

from dataclasses import dataclass
from typing import List, Optional, Dict, Any
from .mesh import MeshState


@dataclass
class UserState:
    """User state in a mesh room"""
    user_id: int
    when_joined: Optional[float] = None
    is_leader: Optional[bool] = None
    order: Optional[int] = None
    voip_enabled: Optional[bool] = None
    
    @classmethod
    def from_dict(cls, data: dict):
        """Create UserState from dictionary"""
        return cls(
            user_id=data.get('user_id'),
            when_joined=data.get('when_joined'),
            is_leader=data.get('is_leader'),
            order=data.get('order'),
            voip_enabled=data.get('voip_enabled')
        )
    
    def to_dict(self) -> dict:
        """Convert UserState to dictionary"""
        result = {'user_id': self.user_id}
        if self.when_joined is not None:
            result['when_joined'] = self.when_joined
        if self.is_leader is not None:
            result['is_leader'] = self.is_leader
        if self.order is not None:
            result['order'] = self.order
        if self.voip_enabled is not None:
            result['voip_enabled'] = self.voip_enabled
        return result


@dataclass
class Vote:
    """Vote information"""
    url: str
    users: List[Dict[str, Any]]
    num_votes: Optional[int] = None
    oldest_vote_time: Optional[float] = None
    order: Optional[int] = None
    
    @classmethod
    def from_dict(cls, data: dict):
        """Create Vote from dictionary"""
        return cls(
            url=data.get('url', ''),
            users=data.get('users', []),
            num_votes=data.get('num_votes'),
            oldest_vote_time=data.get('oldest_vote_time'),
            order=data.get('order')
        )
    
    def to_dict(self) -> dict:
        """Convert Vote to dictionary"""
        result = {
            'url': self.url,
            'users': self.users
        }
        if self.num_votes is not None:
            result['num_votes'] = self.num_votes
        if self.oldest_vote_time is not None:
            result['oldest_vote_time'] = self.oldest_vote_time
        if self.order is not None:
            result['order'] = self.order
        return result


@dataclass
class StateMessage:
    """State message from WebSocket"""
    mesh_state: Optional[MeshState] = None
    users: List[UserState] = None
    votes: List[Vote] = None
    likeskips: List[Dict[str, Any]] = None
    kicks: List[Dict[str, Any]] = None
    cleared_votes: List[Dict[str, Any]] = None
    vote_originator: Optional[int] = None
    __metadata: Optional[Dict[str, Any]] = None
    
    def __post_init__(self):
        """Initialize default values"""
        if self.users is None:
            self.users = []
        if self.votes is None:
            self.votes = []
        if self.likeskips is None:
            self.likeskips = []
        if self.kicks is None:
            self.kicks = []
        if self.cleared_votes is None:
            self.cleared_votes = []
    
    @classmethod
    def from_dict(cls, data: dict):
        """Create StateMessage from dictionary"""
        mesh_state = None
        if 'mesh_state' in data:
            mesh_state = MeshState.from_dict(data['mesh_state'])
        
        users = [UserState.from_dict(u) for u in data.get('users', [])]
        votes = [Vote.from_dict(v) for v in data.get('votes', [])]
        
        return cls(
            mesh_state=mesh_state,
            users=users,
            votes=votes,
            likeskips=data.get('likeskips', []),
            kicks=data.get('kicks', []),
            cleared_votes=data.get('cleared_votes', []),
            vote_originator=data.get('vote_originator'),
            __metadata=data.get('__metadata')
        )
    
    def to_dict(self) -> dict:
        """Convert StateMessage to dictionary"""
        result = {
            'users': [u.to_dict() for u in self.users],
            'votes': [v.to_dict() for v in self.votes],
            'likeskips': self.likeskips,
            'kicks': self.kicks,
            'cleared_votes': self.cleared_votes
        }
        if self.mesh_state is not None:
            result['mesh_state'] = self.mesh_state.to_dict()
        if self.vote_originator is not None:
            result['vote_originator'] = self.vote_originator
        if self.__metadata is not None:
            result['__metadata'] = self.__metadata
        return result

