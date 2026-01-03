"""
Helper functions for Rave API operations
"""

import time
import logging
import mimetypes
import os
from pathlib import Path
from typing import Dict, Any, Optional, List, Union, IO
import requests

from ..api import RaveAPIClient
from ..api.models import MediaUploadRequest, MediaUploadItem, MediaUploadResponse

logger = logging.getLogger(__name__)


# Default API client instance (can be overridden)
_default_api_client: Optional[RaveAPIClient] = None


def set_default_api_client(client: RaveAPIClient):
    """Set the default API client for helper functions"""
    global _default_api_client
    _default_api_client = client


def get_default_api_client() -> RaveAPIClient:
    """Get or create the default API client"""
    global _default_api_client
    if _default_api_client is None:
        _default_api_client = RaveAPIClient()
    return _default_api_client


def get_video_id(info: Dict[str, Any], api_client: Optional[RaveAPIClient] = None) -> str:
    """
    Create a YouTube video entry and get its ID
    
    Args:
        info: Video information dictionary
        api_client: Optional API client instance (uses default if not provided)
        
    Returns:
        Video ID string
    """
    client = api_client or get_default_api_client()
    response = client.post("/videos/youtube", payload=info)
    return response.json().get("data").get("id")


def vote_video(
    video_id: str,
    mesh_id: str,
    device_id: str = "be30981dd1994a48907d4b380d505118",
    api_client: Optional[RaveAPIClient] = None
) -> Dict[str, Any]:
    """
    Vote for a video in a mesh
    
    Args:
        video_id: ID of the video to vote for
        mesh_id: ID of the mesh/room
        device_id: Device ID (default: be30981dd1994a48907d4b380d505118)
        api_client: Optional API client instance (uses default if not provided)
        
    Returns:
        Response JSON dictionary
    """
    client = api_client or get_default_api_client()
    timestamp = int(time.time() * 1000)
    payload = {
        "deviceId": device_id,
        "time": timestamp,
        "url": f"https://api.red.wemesh.ca/videos/youtube/{video_id}"
    }
    response = client.post(f"/meshes/{mesh_id}/votes", payload=payload)
    return response.json()


def get_mesh_info(mesh_id: str, api_client: Optional[RaveAPIClient] = None) -> Dict[str, Any]:
    """
    Get mesh information
    
    Args:
        mesh_id: ID of the mesh/room
        api_client: Optional API client instance (uses default if not provided)
        
    Returns:
        Mesh info dictionary containing server, room_id, users list, and raw_response
    """
    client = api_client or get_default_api_client()
    response = client.get(f"/meshes/{mesh_id}")
    if response.status_code != 200:
        raise Exception(f"Failed to get mesh info: {response.status_code}")
    
    mesh_info = response.json()
    data = mesh_info.get("data", {})
    users = data.get("users", [])
    
    return {
        "server": data.get("server"),
        "room_id": data.get("id"),
        "users": users,
        "raw_response": mesh_info
    }


def get_friendships(limit: int = 50, api_client: Optional[RaveAPIClient] = None) -> Dict[str, Any]:
    """
    Get friendships list
    
    Args:
        limit: Maximum number of friendships to return (default: 50)
        api_client: Optional API client instance (uses default if not provided)
        
    Returns:
        Response JSON dictionary containing friendships data
    """
    client = api_client or get_default_api_client()
    response = client.get("/friendships", params={"limit": limit})
    if response.status_code != 200:
        raise Exception(f"Failed to get friendships: {response.status_code}")
    
    return response.json()


def get_users_list(
    ids: List[int],
    device_id: str = "be30981dd1994a48907d4b380d505118",
    include_online: bool = True,
    api_client: Optional[RaveAPIClient] = None
) -> Dict[str, Any]:
    """
    Get users list by IDs
    
    Args:
        ids: List of user IDs to retrieve
        device_id: Device ID (default: be30981dd1994a48907d4b380d505118)
        include_online: Whether to include online status (default: True)
        api_client: Optional API client instance (uses default if not provided)
        
    Returns:
        Response JSON dictionary containing users data
    """
    client = api_client or get_default_api_client()
    payload = {
        "deviceId": device_id,
        "ids": ids,
        "includeOnline": include_online
    }
    response = client.post("/users/list", payload=payload)
    if response.status_code != 200:
        raise Exception(f"Failed to get users list: {response.status_code}")
    
    return response.json()


def get_meshes(
    device_id: str,
    mode: str = "invited",
    limit: int = 20,
    lang: str = "en",
    api_client: Optional[RaveAPIClient] = None
) -> Dict[str, Any]:
    """
    Get meshes based on mode
    
    Args:
        device_id: Device ID (required)
        mode: "invited" for only invited meshes, "all" for public + friends + invited
        limit: Maximum number of meshes to return (default: 20)
        lang: Language code (default: "en")
        api_client: Optional API client instance (uses default if not provided)
        
    Returns:
        Response JSON dictionary containing list of mesh data with users
        Format: {"data": [{"mesh": {...}, "users": [...]}, ...], "paging": {...}}
    """
    client = api_client or get_default_api_client()
    
    if mode == "all":
        all_meshes = []
        seen_ids = set()
        
        for mesh_type in ["public", "friends", "invited"]:
            params = {
                "deviceId": device_id,
                "public": "true" if mesh_type == "public" else "false",
                "friends": "true" if mesh_type == "friends" else "false",
                "local": "false",
                "invited": "true" if mesh_type == "invited" else "false",
                "limit": limit,
                "lang": lang
            }
            response = client.get("/meshes/self", params=params)
            # print(response.text)
            if response.status_code == 200:
                data = response.json().get("data", [])
                for item in data:
                    mesh = item.get("mesh", {})
                    mesh_id = mesh.get("id")
                    if mesh_id and mesh_id not in seen_ids:
                        all_meshes.append(item)
                        seen_ids.add(mesh_id)
        
        return {"data": all_meshes[:limit], "paging": {}}
    else:
        params = {
            "deviceId": device_id,
            "public": "false",
            "friends": "false",
            "local": "false",
            "invited": "true",
            "limit": limit,
            "lang": lang
        }
        response = client.get("/meshes/self", params=params)
        if response.status_code != 200:
            raise Exception(f"Failed to get meshes: {response.status_code}")
        return response.json()


def get_invited_meshes(
    device_id: str,
    limit: int = 20,
    lang: str = "en",
    api_client: Optional[RaveAPIClient] = None
) -> Dict[str, Any]:
    """
    Get all meshes that the bot has been invited to (deprecated, use get_meshes instead)
    """
    return get_meshes(device_id, mode="invited", limit=limit, lang=lang, api_client=api_client)


def leave_mesh(
    mesh_id: str,
    device_id: str,
    api_client: Optional[RaveAPIClient] = None
) -> bool:
    """
    Leave a mesh
    
    Args:
        mesh_id: Mesh ID to leave
        device_id: Device ID (required)
        api_client: Optional API client instance (uses default if not provided)
        
    Returns:
        True if successful, False otherwise
    """
    client = api_client or get_default_api_client()
    response = client.delete(f"/meshes/{mesh_id}/devices/{device_id}/leave")
    if response.status_code == 200:
        return True
    else:
        logger.warning(f"Failed to leave mesh {mesh_id}: {response.status_code}")
        return False


def _detect_mime_type(file_path_or_obj: Union[str, IO]) -> str:
    """
    Detect MIME type from file path or object
    
    Args:
        file_path_or_obj: File path string or file-like object
        
    Returns:
        MIME type string (defaults to 'application/octet-stream')
    """
    if isinstance(file_path_or_obj, str):
        mime_type, _ = mimetypes.guess_type(file_path_or_obj)
        if mime_type:
            return mime_type
        # Fallback for common extensions
        ext = Path(file_path_or_obj).suffix.lower()
        mime_map = {
            '.mp4': 'video/mp4',
            '.mov': 'video/quicktime',
            '.avi': 'video/x-msvideo',
            '.webm': 'video/webm',
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.png': 'image/png',
            '.gif': 'image/gif',
            '.webp': 'image/webp'
        }
        return mime_map.get(ext, 'application/octet-stream')
    else:
        # File-like object - try to get name attribute
        if hasattr(file_path_or_obj, 'name') and file_path_or_obj.name:
            return _detect_mime_type(file_path_or_obj.name)
        return 'application/octet-stream'


def upload_media(
    mesh_id: str,
    media_files: List[Union[str, IO]],
    is_explicit: bool = False,
    api_client: Optional[RaveAPIClient] = None
) -> List[Dict[str, Any]]:
    """
    Upload media files (images/videos) to a mesh
    
    This function handles the complete upload flow:
    1. Requests upload URLs from the API
    2. Uploads each file to the returned S3 upload URLs
    3. Returns posting URLs ready for use in chat messages
    
    Args:
        mesh_id: ID of the mesh/room
        media_files: List of file paths (str) or file-like objects to upload
        is_explicit: Whether the media is explicit (default: False)
        api_client: Optional API client instance (uses default if not provided)
        
    Returns:
        List of dictionaries containing media info for chat messages:
        [
            {
                "url": "https://ugc2.prod.hilljam.com/...",
                "mime": "video/mp4",
                "isExplicit": False,
                "aspectRatio": "0.56",  # Optional, may need to be calculated
                "thumbnailUrl": "..."  # Optional, may be empty for images
            },
            ...
        ]
        
    Raises:
        Exception: If upload fails at any stage
    """
    client = api_client or get_default_api_client()
    
    # Step 1: Prepare upload request
    media_items = []
    for index, file_obj in enumerate(media_files):
        mime_type = _detect_mime_type(file_obj)
        media_items.append(MediaUploadItem(
            index=index,
            mime=mime_type,
            isExplicit=is_explicit
        ))
    
    upload_request = MediaUploadRequest(media=media_items)
    
    # Step 2: Request upload URLs
    response = client.post(
        f"/meshes/{mesh_id}/images/upload",
        payload=upload_request.to_dict()
    )
    
    if response.status_code != 200:
        raise Exception(f"Failed to get upload URLs: {response.status_code} - {response.text}")
    
    upload_response = MediaUploadResponse.from_response(response)
    
    # Step 3: Upload each file to S3
    posting_urls = []
    for upload_item in upload_response.data:
        # Find the corresponding file
        file_obj = media_files[upload_item.index]
        
        # Read file content
        if isinstance(file_obj, str):
            # File path - open and read
            with open(file_obj, 'rb') as f:
                file_content = f.read()
        else:
            # File-like object - read from current position
            current_pos = file_obj.tell()
            file_obj.seek(0)
            file_content = file_obj.read()
            file_obj.seek(current_pos)  # Restore position
        
        # Upload to S3 using PUT request
        upload_response_http = requests.put(
            upload_item.uploadUrl,
            data=file_content,
            headers={'Content-Type': upload_item.mime}
        )
        
        if upload_response_http.status_code not in [200, 204]:
            raise Exception(
                f"Failed to upload file {upload_item.index} to S3: "
                f"{upload_response_http.status_code} - {upload_response_http.text}"
            )
        
        # Prepare media info for chat message
        media_info = {
            "url": upload_item.postingUrl,
            "mime": upload_item.mime,
            "isExplicit": is_explicit,
            "aspectRatio": "",  # May need to be calculated from image/video dimensions
            "thumbnailUrl": ""  # May be provided for videos, empty for images
        }
        
        posting_urls.append(media_info)
    
    return posting_urls