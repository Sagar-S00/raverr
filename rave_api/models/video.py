"""
Video model for Rave API
"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class Video:
    """Video information model"""
    id: str
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
        """Create Video from dictionary"""
        return cls(
            id=data.get('id', ''),
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
        """Convert Video to dictionary"""
        result = {'id': self.id}
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

