"""
API response models for Rave API
"""

from dataclasses import dataclass
from typing import Optional, Any, Dict, List
from datetime import datetime


@dataclass
class APIResponse:
    """Base API response model"""
    data: Any = None
    status: Optional[int] = None
    message: Optional[str] = None
    success: Optional[bool] = None
    
    @classmethod
    def from_response(cls, response):
        """Create APIResponse from requests.Response"""
        try:
            json_data = response.json()
            return cls(
                data=json_data.get('data'),
                status=response.status_code,
                message=json_data.get('message'),
                success=json_data.get('success', response.status_code == 200)
            )
        except Exception:
            return cls(
                data=None,
                status=response.status_code,
                message=None,
                success=False
            )
    
    def to_dict(self) -> dict:
        """Convert APIResponse to dictionary"""
        result = {}
        if self.data is not None:
            result['data'] = self.data
        if self.status is not None:
            result['status'] = self.status
        if self.message is not None:
            result['message'] = self.message
        if self.success is not None:
            result['success'] = self.success
        return result


@dataclass
class MediaUploadItem:
    """Media item for upload request"""
    index: int
    mime: str
    isExplicit: bool = False
    
    def to_dict(self) -> dict:
        """Convert to dictionary for API request"""
        return {
            "index": self.index,
            "isExplicit": self.isExplicit,
            "mime": self.mime
        }


@dataclass
class MediaUploadRequest:
    """Request model for media upload endpoint"""
    media: List[MediaUploadItem]
    
    def to_dict(self) -> dict:
        """Convert to dictionary for API request"""
        return {
            "media": [item.to_dict() for item in self.media]
        }


@dataclass
class MediaUploadItemResponse:
    """Response item for media upload"""
    expiresAt: str
    fileName: str
    index: int
    mime: str
    postingUrl: str
    uploadUrl: str
    
    @classmethod
    def from_dict(cls, data: dict):
        """Create MediaUploadItemResponse from dictionary"""
        return cls(
            expiresAt=data.get('expiresAt', ''),
            fileName=data.get('fileName', ''),
            index=data.get('index', 0),
            mime=data.get('mime', ''),
            postingUrl=data.get('postingUrl', ''),
            uploadUrl=data.get('uploadUrl', '')
        )
    
    def to_dict(self) -> dict:
        """Convert to dictionary"""
        return {
            "expiresAt": self.expiresAt,
            "fileName": self.fileName,
            "index": self.index,
            "mime": self.mime,
            "postingUrl": self.postingUrl,
            "uploadUrl": self.uploadUrl
        }


@dataclass
class MediaUploadResponse:
    """Response model for media upload endpoint"""
    data: List[MediaUploadItemResponse]
    
    @classmethod
    def from_response(cls, response):
        """Create MediaUploadResponse from requests.Response"""
        try:
            json_data = response.json()
            data_list = json_data.get('data', [])
            return cls(
                data=[MediaUploadItemResponse.from_dict(item) for item in data_list]
            )
        except Exception as e:
            raise ValueError(f"Failed to parse media upload response: {e}")
    
    def to_dict(self) -> dict:
        """Convert to dictionary"""
        return {
            "data": [item.to_dict() for item in self.data]
        }

