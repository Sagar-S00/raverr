"""
Rave API Client Module
Handles all API requests with automatic header generation and request hash signing
"""

import json
import time
import hmac
import hashlib
import base64
from typing import Dict, Any, Optional, Union
import requests
from requests import Response

# Try to import brotli for manual decompression if needed
try:
    import brotli
    BROTLI_AVAILABLE = True
except ImportError:
    BROTLI_AVAILABLE = False


class RaveAPIClient:
    """
    Rave API Client
    
    Automatically handles:
    - Request-Hash generation
    - Request-Ts (timestamp) generation
    - All required headers
    - Request signing
    """
    
    # Secret key for HMAC-SHA256 hash generation (from RequestHasher.java)
    SECRET_KEY = "c3ab8ff13720e8ad9047dd39466b3c8974e592c2fa383d4a3960714caef0c4f2"
    
    def __init__(
        self,
        base_url: str = "https://api.red.wemesh.ca",
        auth_token: str = "",
        client_version: str = "8.2.9",
        api_version: str = "4.0",
        platform: str = "android",
        user_agent: str = "Rave/2149 (8.2.9) (Android 9; ASUS_X00TD; asus ASUS_X00T_2; en)",
        ssaid: str = "b32a05e5c198bdc0"
    ):
        """
        Initialize Rave API Client
        
        Args:
            base_url: Base URL for the API (default: https://api.red.wemesh.ca)
            auth_token: Bearer token for authentication
            client_version: Client version (default: 8.2.9)
            api_version: API version (default: 4.0)
            platform: Platform name (default: android)
            user_agent: User-Agent string
            ssaid: SSaid header value
        """
        self.base_url = base_url.rstrip('/')
        self.auth_token = auth_token
        self.client_version = client_version
        self.api_version = api_version
        self.platform = platform
        self.user_agent = user_agent
        self.ssaid = ssaid
        
        # Create session for connection pooling
        self.session = requests.Session()
        
        # Ensure brotli support is available
        if BROTLI_AVAILABLE:
            # requests should automatically use brotli if available
            # But we'll handle manual decompression as fallback
            pass
    
    def _generate_request_hash(self, timestamp: int, token: str, content_length: int) -> str:
        """
        Generate Request-Hash using HMAC-SHA256
        
        Based on RequestHasher.generateHash() from the Android app.
        Format: HMAC-SHA256("{timestamp}:{token}:{contentLength}")
        
        Args:
            timestamp: Request timestamp in milliseconds
            token: Auth token
            content_length: Content length of request body
            
        Returns:
            Base64 encoded hash
        """
        input_string = f"{timestamp}:{token}:{content_length}"
        
        # Create HMAC-SHA256
        mac = hmac.new(
            self.SECRET_KEY.encode('utf-8'),
            input_string.encode('utf-8'),
            hashlib.sha256
        )
        
        # Get Base64 encoded result (NO_WRAP = no padding/newlines)
        hash_bytes = mac.digest()
        hash_base64 = base64.b64encode(hash_bytes).decode('utf-8')
        
        return hash_base64
    
    def _generate_timestamp(self) -> int:
        """
        Generate current timestamp in milliseconds
        
        Returns:
            Timestamp in milliseconds
        """
        return int(time.time() * 1000)
    
    def _build_headers(
        self,
        method: str,
        payload: Optional[Union[Dict, str]] = None,
        custom_headers: Optional[Dict[str, str]] = None
    ) -> Dict[str, str]:
        """
        Build request headers with automatic hash generation
        
        Args:
            method: HTTP method (GET, POST, DELETE, etc.)
            payload: Request payload (dict or JSON string)
            custom_headers: Additional custom headers to include
            
        Returns:
            Dictionary of headers
        """
        # Calculate content length
        # Must match exactly what requests library sends when using json=payload
        # requests uses json.dumps() with default settings (includes spaces)
        if payload is None:
            content_length = 0
        elif isinstance(payload, dict):
            content_length = len(json.dumps(payload))
        else:
            content_length = len(str(payload))
        
        # Generate timestamp and hash
        timestamp = self._generate_timestamp()
        
        request_hash = self._generate_request_hash(timestamp, self.auth_token, content_length)
        
        
        # Build base headers
        headers = {
            "Host": self.base_url.replace("https://", "").replace("http://", ""),
            "Client-Version": self.client_version,
            "Wemesh-Api-Version": self.api_version,
            "Wemesh-Platform": self.platform,
            "User-Agent": self.user_agent,
            "Ssaid": self.ssaid,
            "Authorization": f"Bearer {self.auth_token}",
            "Request-Hash": request_hash,
            "Request-Ts": str(timestamp),
            "Accept-Encoding": "gzip, deflate, br",
        }
        
        # Add Content-Type for requests with body
        if method.upper() in ["POST", "PUT", "PATCH"] and payload is not None:
            headers["Content-Type"] = "application/json; charset=UTF-8"
        
        # Merge custom headers (custom headers take precedence)
        if custom_headers:
            headers.update(custom_headers)
        
        return headers
    
    def _ensure_decompressed(self, response: Response) -> Response:
        """
        Ensure response is properly decompressed, especially for Brotli encoding.
        
        The requests library should automatically decompress, but sometimes it doesn't
        work properly with Brotli. This method manually decompresses if needed.
        
        Args:
            response: Response object
            
        Returns:
            Response object with properly decompressed content
        """
        # Check if response is Brotli-compressed
        content_encoding = response.headers.get('Content-Encoding', '').lower()
        
        if 'br' in content_encoding and BROTLI_AVAILABLE and response.content:
            try:
                # Try to check if content is already decompressed by attempting JSON parse
                # If it fails, try manual decompression
                try:
                    # Try to decode as text first
                    text = response.text
                    # If it doesn't look like valid JSON/text, try decompressing
                    if text and not (text.strip().startswith('{') or text.strip().startswith('[') or text.strip().startswith('"')):
                        # Content might still be compressed
                        decompressed = brotli.decompress(response.content)
                        response._content = decompressed
                        response.headers.pop('Content-Encoding', None)
                        # Clear the cached text so it gets regenerated
                        response._text = None
                except (UnicodeDecodeError, AttributeError):
                    # Content is binary/compressed, decompress it
                    decompressed = brotli.decompress(response.content)
                    response._content = decompressed
                    response.headers.pop('Content-Encoding', None)
                    response._text = None
            except Exception:
                # If decompression fails for any reason, return original response
                # This could happen if content is already decompressed or not actually brotli
                pass
        
        return response
    
    def get(
        self,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        timeout: int = 15
    ) -> Response:
        """
        Send GET request
        
        Args:
            endpoint: API endpoint (e.g., "/meshes/{mesh-id}")
            params: Query parameters
            headers: Additional custom headers
            timeout: Request timeout in seconds
            
        Returns:
            Response object
        """
        url = f"{self.base_url}{endpoint}"
        request_headers = self._build_headers("GET", custom_headers=headers)
        
        response = self.session.get(
            url,
            headers=request_headers,
            params=params,
            timeout=timeout
        )
        
        # Ensure response is properly decompressed
        response = self._ensure_decompressed(response)
        
        return response
    
    def post(
        self,
        endpoint: str,
        payload: Optional[Union[Dict, str]] = None,
        headers: Optional[Dict[str, str]] = None,
        timeout: int = 15
    ) -> Response:
        """
        Send POST request
        
        Args:
            endpoint: API endpoint (e.g., "/meshes/{mesh-id}/kick")
            payload: Request body (dict or JSON string)
            headers: Additional custom headers
            timeout: Request timeout in seconds
            
        Returns:
            Response object
        """
        url = f"{self.base_url}{endpoint}"
        request_headers = self._build_headers("POST", payload=payload, custom_headers=headers)
        
        # Handle payload
        if payload is None:
            json_data = None
            data = None
        elif isinstance(payload, dict):
            json_data = payload
            data = None
        else:
            json_data = None
            data = payload
        
        response = self.session.post(
            url,
            headers=request_headers,
            json=json_data,
            data=data,
            timeout=timeout
        )
        
        # Ensure response is properly decompressed
        response = self._ensure_decompressed(response)
        
        return response
    
    def put(
        self,
        endpoint: str,
        payload: Optional[Union[Dict, str]] = None,
        headers: Optional[Dict[str, str]] = None,
        timeout: int = 15
    ) -> Response:
        """
        Send PUT request
        
        Args:
            endpoint: API endpoint
            payload: Request body (dict or JSON string)
            headers: Additional custom headers
            timeout: Request timeout in seconds
            
        Returns:
            Response object
        """
        url = f"{self.base_url}{endpoint}"
        request_headers = self._build_headers("PUT", payload=payload, custom_headers=headers)
        
        # Handle payload
        if payload is None:
            json_data = None
            data = None
        elif isinstance(payload, dict):
            json_data = payload
            data = None
        else:
            json_data = None
            data = payload
        
        response = self.session.put(
            url,
            headers=request_headers,
            json=json_data,
            data=data,
            timeout=timeout
        )
        
        # Ensure response is properly decompressed
        response = self._ensure_decompressed(response)
        
        return response
    
    def delete(
        self,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        timeout: int = 15
    ) -> Response:
        """
        Send DELETE request
        
        Args:
            endpoint: API endpoint
            params: Query parameters
            headers: Additional custom headers
            timeout: Request timeout in seconds
            
        Returns:
            Response object
        """
        url = f"{self.base_url}{endpoint}"
        request_headers = self._build_headers("DELETE", custom_headers=headers)
        
        response = self.session.delete(
            url,
            headers=request_headers,
            params=params,
            timeout=timeout
        )
        
        # Ensure response is properly decompressed
        response = self._ensure_decompressed(response)
        
        return response
    
    def patch(
        self,
        endpoint: str,
        payload: Optional[Union[Dict, str]] = None,
        headers: Optional[Dict[str, str]] = None,
        timeout: int = 15
    ) -> Response:
        """
        Send PATCH request
        
        Args:
            endpoint: API endpoint
            payload: Request body (dict or JSON string)
            headers: Additional custom headers
            timeout: Request timeout in seconds
            
        Returns:
            Response object
        """
        url = f"{self.base_url}{endpoint}"
        request_headers = self._build_headers("PATCH", payload=payload, custom_headers=headers)
        
        # Handle payload
        if payload is None:
            json_data = None
            data = None
        elif isinstance(payload, dict):
            json_data = payload
            data = None
        else:
            json_data = None
            data = payload
        
        response = self.session.patch(
            url,
            headers=request_headers,
            json=json_data,
            data=data,
            timeout=timeout
        )
        
        # Ensure response is properly decompressed
        response = self._ensure_decompressed(response)
        
        return response
    
    def close(self):
        """Close the session"""
        self.session.close()
    
    def __enter__(self):
        """Context manager entry"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.close()

