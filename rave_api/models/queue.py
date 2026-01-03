"""
Queue model for Rave API
"""

from dataclasses import dataclass
from typing import List, Optional
from .video import Video


@dataclass
class QueueItem:
    """Queue item model"""
    id: str
    position: Optional[int] = None
    title: Optional[str] = None
    author: Optional[str] = None
    url: Optional[str] = None
    thumbnail: Optional[str] = None
    viewCount: Optional[str] = None
    duration: Optional[str] = None
    provider: Optional[str] = None
    isLive: Optional[bool] = None
    
    @classmethod
    def from_dict(cls, data: dict):
        """Create QueueItem from dictionary"""
        return cls(
            id=data.get('id', ''),
            position=data.get('position'),
            title=data.get('title'),
            author=data.get('author'),
            url=data.get('url'),
            thumbnail=data.get('thumbnail'),
            viewCount=data.get('viewCount'),
            duration=data.get('duration'),
            provider=data.get('provider'),
            isLive=data.get('isLive')
        )
    
    def to_dict(self) -> dict:
        """Convert QueueItem to dictionary"""
        result = {'id': self.id}
        if self.position is not None:
            result['position'] = self.position
        if self.title is not None:
            result['title'] = self.title
        if self.author is not None:
            result['author'] = self.author
        if self.url is not None:
            result['url'] = self.url
        if self.thumbnail is not None:
            result['thumbnail'] = self.thumbnail
        if self.viewCount is not None:
            result['viewCount'] = self.viewCount
        if self.duration is not None:
            result['duration'] = self.duration
        if self.provider is not None:
            result['provider'] = self.provider
        if self.isLive is not None:
            result['isLive'] = self.isLive
        return result


@dataclass
class Queue:
    """Queue message model"""
    queueId: str
    items: List[QueueItem]
    transactionTs: Optional[str] = None
    lastIndex: Optional[int] = None
    
    @classmethod
    def from_dict(cls, data: dict):
        """Create Queue from dictionary"""
        items = [QueueItem.from_dict(item) for item in data.get('items', [])]
        return cls(
            queueId=data.get('queueId', ''),
            items=items,
            transactionTs=data.get('transactionTs'),
            lastIndex=data.get('lastIndex')
        )
    
    def to_dict(self) -> dict:
        """Convert Queue to dictionary"""
        result = {
            'queueId': self.queueId,
            'items': [item.to_dict() for item in self.items]
        }
        if self.transactionTs is not None:
            result['transactionTs'] = self.transactionTs
        if self.lastIndex is not None:
            result['lastIndex'] = self.lastIndex
        return result

