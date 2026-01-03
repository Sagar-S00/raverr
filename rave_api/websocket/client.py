"""
Rave WebSocket Client Module
Based on the Android Rave app source code

This module implements the WebSocket connection protocol used by Rave for mesh rooms.
It handles connection, keep-alive, join messages, and reconnection logic.
"""

import asyncio
import json
import logging
import ssl
import uuid
import platform  # Add this import
from typing import Callable, Dict, Optional, Any, List
from urllib.parse import urlencode

import websockets
from websockets.client import WebSocketClientProtocol
from websockets.exceptions import ConnectionClosed, WebSocketException

from .protoo import ProtooRequest, ProtooNotification

logger = logging.getLogger(__name__)

# Check websockets version for compatibility
try:
    import websockets.version
    WEBSOCKETS_VERSION = tuple(map(int, websockets.version.version.split('.')))
except (AttributeError, ImportError, ValueError):
    # Fallback: assume version 12.0+
    WEBSOCKETS_VERSION = (12, 0, 0)

# Detect OS
IS_LINUX = platform.system().lower() == 'linux'


class RaveWebSocketClient:
    """
    WebSocket client for Rave mesh rooms
    
    Based on SocketManager.java and RoomClient.java from the Android app.
    """
    
    def __init__(
        self,
        server: str,
        room_id: str,
        peer_id: str,
        auth_token: str = "",
        debug: bool = False,
        on_message: Optional[Callable[[Dict[str, Any]], None]] = None,
        on_connected: Optional[Callable[[], None]] = None,
        on_disconnected: Optional[Callable[[], None]] = None,
        on_error: Optional[Callable[[Exception], None]] = None
    ):
        """
        Initialize Rave WebSocket client
        
        Args:
            server: WebSocket server hostname (e.g., "wss://server.com")
            room_id: Mesh room ID
            peer_id: Peer ID (required)
                    Format: {userId}_{uuid}
                    Based on RoomConfig.java: GatekeeperServer.getInstance().getLoggedInUser().getId() + "_" + Utility.getUUID()
            auth_token: Bearer token for authentication
            debug: Enable debug logging (default: False)
            on_message: Callback for received messages
            on_connected: Callback when connected
            on_disconnected: Callback when disconnected
            on_error: Callback for errors
        """
        self.server = server
        self.room_id = room_id
        self.peer_id = peer_id
        self.auth_token = auth_token
        self.debug = debug
        
        # Callbacks
        self.on_message = on_message
        self.on_connected = on_connected
        self.on_disconnected = on_disconnected
        self.on_error = on_error
        
        # Connection state
        self.websocket: Optional[WebSocketClientProtocol] = None
        self.is_connected = False
        self.is_terminated = False
        self._disconnect_lock = asyncio.Lock()  # Lock to prevent race conditions in disconnect
        
        # Reconnection strategy (exponential backoff)
        self.initial_backoff = 1.0  # 1 second
        self.max_backoff = 12.5  # 12.5 seconds
        self.retry_count = 0
        self.max_retries = 10
        
        # Ping interval (15 seconds as per SocketManager)
        self.ping_interval = 15.0
        self.ping_task: Optional[asyncio.Task] = None
        self.listen_task: Optional[asyncio.Task] = None
        
        # Response channels for request/response pattern
        self.response_channels: Dict[int, asyncio.Queue] = {}
        
    def _build_url(self) -> str:
        """Build WebSocket URL based on RoomConfig.toProtooUrl()"""
        params = {
            "roomId": self.room_id,
            "peerId": self.peer_id
        }
        query_string = urlencode(params)
        
        # Format: wss://{server}:443/?roomId={roomId}&peerId={peerId}
        if self.server.startswith("wss://") or self.server.startswith("ws://"):
            base_url = self.server
        else:
            base_url = f"wss://{self.server}"
        
        # Ensure port 443 is specified
        if ":443" not in base_url and not base_url.endswith(":443"):
            if base_url.startswith("wss://"):
                base_url = base_url.replace("wss://", "wss://") + ":443"
            else:
                base_url = base_url + ":443"
        
        return f"{base_url}/?{query_string}"
    
    def _build_headers(self) -> Dict[str, str]:
        """Build WebSocket headers as per SocketManager.createRequest()"""
        headers = {
            "Authorization": f"Bearer {self.auth_token}" if self.auth_token else "",
            "API-Version": "4"
        }
        
        # On Linux, include Sec-WebSocket-Protocol in headers (current working behavior)
        # On Windows, let subprotocols parameter handle it to avoid HTTP 400
        if IS_LINUX:
            headers["Sec-WebSocket-Protocol"] = "protoo"
        
        return headers
    
    def _create_ssl_context(self) -> ssl.SSLContext:
        """Create SSL context that accepts all certificates (like the app does)"""
        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE
        return ssl_context
    
    async def connect(self) -> bool:
        """Connect to WebSocket server"""
        if self.is_connected:
            logger.warning("Already connected")
            return True
        
        if self.is_terminated:
            logger.error("Connection terminated, cannot reconnect")
            return False
        
        url = self._build_url()
        headers = self._build_headers()
        
        if self.debug:
            logger.info(f"Connecting to {url}")
        
        try:
            # Create SSL context
            ssl_context = self._create_ssl_context()
            
            # Connect with custom headers and subprotocol
            # The "protoo" subprotocol is required (from SocketManager.java line 163)
            # Use additional_headers for websockets 12.0+, but handle version differences
            connect_kwargs = {
                "subprotocols": ["protoo"],  # Required subprotocol
                "ssl": ssl_context,
                "ping_interval": None  # We'll handle ping manually
            }
            
            # Add headers based on websockets version
            # websockets 12.0+ uses additional_headers
            if WEBSOCKETS_VERSION >= (12, 0, 0):
                connect_kwargs["additional_headers"] = headers
            else:
                # Older versions might use extra_headers or handle it differently
                connect_kwargs["extra_headers"] = headers
            
            try:
                self.websocket = await websockets.connect(url, **connect_kwargs)
            except (TypeError, ValueError) as e:
                # If additional_headers/extra_headers doesn't work, try without it
                # This might happen if the version check was wrong or there's a bug
                error_msg = str(e)
                if "extra_headers" in error_msg or "additional_headers" in error_msg or "unexpected keyword" in error_msg:
                    if self.debug:
                        logger.warning(f"Headers parameter not supported: {e}, trying without headers")
                    connect_kwargs.pop("additional_headers", None)
                    connect_kwargs.pop("extra_headers", None)
                    self.websocket = await websockets.connect(url, **connect_kwargs)
                    if self.debug:
                        logger.warning("Connected without custom headers - authentication might fail")
                else:
                    # Re-raise if it's a different error
                    raise
            
            self.is_connected = True
            self.retry_count = 0  # Reset retry count on successful connection
            
            if self.debug:
                logger.info("WebSocket connected successfully")
            
            # Start ping task
            self.ping_task = asyncio.create_task(self._ping_loop())
            
            # Start listen task in background to receive responses
            self.listen_task = asyncio.create_task(self._listen())
            
            # Call on_connected callback
            if self.on_connected:
                self.on_connected()
            
            # Send fullyJoined message after connection (as per RoomClient.sendFullyJoined)
            await self.send_fully_joined()
            
            return True
            
        except Exception as e:
            error_type = type(e).__name__
            error_msg = str(e)
            if "timeout" in error_msg.lower() or "timed out" in error_msg.lower():
                logger.error(f"Connection failed: timed out during opening handshake")
            elif "SSL" in error_type or "ssl" in error_msg.lower() or "certificate" in error_msg.lower():
                logger.error(f"Connection failed: SSL/TLS error - {error_msg}")
            elif "401" in error_msg or "403" in error_msg or "unauthorized" in error_msg.lower() or "forbidden" in error_msg.lower():
                logger.error(f"Connection failed: Authentication error - {error_msg}")
            elif "Connection refused" in error_msg or "refused" in error_msg.lower():
                logger.error(f"Connection failed: Connection refused - server may be down or unreachable")
            elif "Name resolution" in error_msg or "DNS" in error_msg or "getaddrinfo" in error_msg:
                logger.error(f"Connection failed: DNS resolution error - {error_msg}")
            else:
                logger.error(f"Connection failed: {error_type} - {error_msg}")
            self.is_connected = False
            if self.on_error:
                self.on_error(e)
            return False
    
    async def _ping_loop(self):
        """Send periodic ping messages to keep connection alive (15 second interval)"""
        try:
            # Wait for initial interval before first ping (don't send immediately)
            # This matches the app behavior - pings start after connection is established
            await asyncio.sleep(self.ping_interval)
            
            while self.is_connected and not self.is_terminated:
                if self.is_connected and self.websocket:
                    try:
                        # Send clientPing request
                        # Based on history: {"data":{},"id":9092465,"method":"clientPing","request":true}
                        ping_request = ProtooRequest("clientPing", {})
                        message = ping_request.to_json()
                        await self.websocket.send(message)
                        if self.debug:
                            logger.debug(f"Sent ping (id: {ping_request.id})")
                    except Exception as e:
                        logger.error(f"Ping failed: {e}")
                        break
                
                # Wait for next ping interval (15 seconds)
                await asyncio.sleep(self.ping_interval)
        except asyncio.CancelledError:
            logger.debug("Ping loop cancelled")
    
    async def send_request(self, request: ProtooRequest) -> Optional[Dict[str, Any]]:
        """
        Send a ProtooRequest and wait for response
        
        Args:
            request: ProtooRequest to send
            
        Returns:
            Response data or None if error
        """
        # Check both is_connected and is_terminated to prevent race conditions
        if self.is_terminated or not self.is_connected or not self.websocket:
            logger.error("Not connected or terminated, cannot send request")
            return None
        
        try:
            # Create response channel
            response_queue = asyncio.Queue()
            self.response_channels[request.id] = response_queue
            
            # Send request
            message = request.to_json()
            # Check again right before sending to catch race conditions
            if self.is_terminated or not self.is_connected or not self.websocket:
                if request.id in self.response_channels:
                    del self.response_channels[request.id]
                return None
            await self.websocket.send(message)
            if self.debug:
                logger.debug(f"Sent request: {message}")
            
            # Wait for response with timeout
            try:
                response = await asyncio.wait_for(response_queue.get(), timeout=8.0)
                return response
            except asyncio.TimeoutError:
                logger.error(f"Request {request.id} timed out")
                return None
            finally:
                # Clean up response channel
                if request.id in self.response_channels:
                    del self.response_channels[request.id]
                    
        except ConnectionClosed as e:
            self.is_connected = False
            logger.error(f"Connection closed while sending request: {e}")
            if request.id in self.response_channels:
                del self.response_channels[request.id]
            return None
        except Exception as e:
            logger.error(f"Error sending request: {e}")
            if request.id in self.response_channels:
                del self.response_channels[request.id]
            return None
    
    async def send_notification(self, notification: ProtooNotification):
        """
        Send a ProtooNotification (fire and forget)
        
        Args:
            notification: ProtooNotification to send
        """
        # Check both is_connected and is_terminated to prevent race conditions
        if self.is_terminated or not self.is_connected or not self.websocket:
            logger.error("Not connected or terminated, cannot send notification")
            return
        
        try:
            message = notification.to_json()
            # Check again right before sending to catch race conditions
            if self.is_terminated or not self.is_connected or not self.websocket:
                return
            await self.websocket.send(message)
            if self.debug:
                logger.debug(f"Sent notification: {message}")
        except ConnectionClosed as e:
            self.is_connected = False
            logger.error(f"Connection closed while sending notification: {e}")
            return
        except Exception as e:
            logger.error(f"Error sending notification: {e}")
    
    async def send_fully_joined(self):
        """Send fullyJoined request after connection (as per RoomClient.sendFullyJoined)"""
        request = ProtooRequest("fullyJoined", {})
        response = await self.send_request(request)
        if response:
            if self.debug:
                logger.info("fullyJoined response received")
        elif self.debug:
            logger.warning("fullyJoined request failed or timed out")
    
    async def send_chat_message(
        self,
        message: str,
        user_id: Optional[str] = None,
        reply_to: Optional[str] = None,
        media: Optional[List[Dict[str, Any]]] = None
    ) -> str:
        """
        Send a chat message
        
        Args:
            message: Chat message text
            user_id: Optional user ID
            reply_to: Optional message ID to reply to
            media: Optional list of media items to include in message.
                   Format: [{"url": "...", "mime": "...", "isExplicit": False, "aspectRatio": "...", "thumbnailUrl": "..."}, ...]
            
        Returns:
            Message ID that was sent (may be different from server's assigned ID)
        """
        # Based on history: {"data":{"chat":"...","detected_lang":"en","id":"...","reply":"...","translations":{},"media":[...]},"method":"chatMessage","notification":true}
        message_id = str(uuid.uuid4())
        data = {
            "chat": message,
            "detected_lang": "en",  # Could be detected, but defaulting to "en"
            "id": message_id,
            "translations": {}
        }
        if user_id:
            data["userId"] = user_id
        if reply_to:
            data["reply"] = reply_to
        if media:
            data["media"] = media
        
        notification = ProtooNotification("chatMessage", data)
        await self.send_notification(notification)
        return message_id
    
    async def send_typing_state(self, is_typing: bool):
        """
        Send typing state notification
        
        Args:
            is_typing: True if user is typing
        """
        # Based on history: "typing" or "typing_stop" (not "userTyping"/"userStoppedTyping")
        method = "typing" if is_typing else "typing_stop"
        notification = ProtooNotification(method, {})
        await self.send_notification(notification)
    
    async def _handle_message(self, message: str):
        """Handle incoming WebSocket message"""
        try:
            data = json.loads(message)
            
            # Check if it's a response to a pending request
            if "id" in data and "response" in data:
                request_id = data["id"]
                if request_id in self.response_channels:
                    await self.response_channels[request_id].put(data)
                    return
            
            # Handle notifications and requests from server
            if self.on_message:
                self.on_message(data)
            elif self.debug:
                logger.debug(f"Received message: {message}")
                
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse message: {e}")
        except Exception as e:
            logger.error(f"Error handling message: {e}")
    
    async def _listen(self):
        """Listen for incoming messages"""
        try:
            async for message in self.websocket:
                if isinstance(message, str):
                    await self._handle_message(message)
                else:
                    logger.warning(f"Received non-text message: {type(message)}")
        except ConnectionClosed as e:
            logger.info("WebSocket connection closed")
            # Only update state if not already terminated (to avoid race with disconnect())
            if not self.is_terminated:
                self.is_connected = False
            if self.on_disconnected:
                self.on_disconnected()
        except Exception as e:
            logger.error(f"Error in listen loop: {e}")
            if not self.is_terminated:
                self.is_connected = False
            if self.on_error:
                self.on_error(e)
            if self.on_disconnected:
                self.on_disconnected()
    
    async def disconnect(self, code: int = 1000, reason: str = "Normal closure"):
        """Disconnect from WebSocket"""
        # Use lock to make disconnect atomic and prevent race conditions
        async with self._disconnect_lock:
            # Make idempotent - if already terminated, return early
            if self.is_terminated:
                return
            # Set is_connected to False IMMEDIATELY to prevent any sends
            self.is_connected = False
            self.is_terminated = True
            
            # All disconnect work must be inside the lock to prevent race conditions
            if self.ping_task:
                self.ping_task.cancel()
                try:
                    await self.ping_task
                except asyncio.CancelledError:
                    pass
            
            if self.listen_task:
                self.listen_task.cancel()
                try:
                    await self.listen_task
                except asyncio.CancelledError:
                    pass
            
            if self.websocket:
                try:
                    await self.websocket.close(code=code, reason=reason)
                except ConnectionClosed:
                    # Already closed, that's fine
                    pass
                except Exception as e:
                    logger.error(f"Error closing WebSocket: {e}")
                finally:
                    self.websocket = None
        
        logger.info("Disconnected from WebSocket")
    
    def _calculate_backoff(self) -> float:
        """Calculate exponential backoff time"""
        backoff = min(
            self.initial_backoff * (1.5 ** self.retry_count),
            self.max_backoff
        )
        return backoff
    
    async def reconnect(self):
        """Reconnect with exponential backoff"""
        if self.is_terminated:
            logger.warning("Connection terminated, cannot reconnect")
            return
        
        if self.retry_count >= self.max_retries:
            logger.error("Max retries reached, giving up")
            return
        
        backoff = self._calculate_backoff()
        self.retry_count += 1
        
        logger.info(f"Reconnecting in {backoff:.2f} seconds (attempt {self.retry_count})")
        await asyncio.sleep(backoff)
        
        # Close existing connection if any
        if self.websocket:
            try:
                await self.websocket.close(code=1000, reason="Reconnecting")
            except:
                pass
        
        # Reconnect
        await self.connect()
    
    async def run(self):
        """Run the WebSocket client (connect and listen)"""
        await self.connect()
        
        if self.is_connected:
            await self._listen()
        
        # Auto-reconnect if not terminated
        if not self.is_terminated and not self.is_connected:
            await self.reconnect()
            if self.is_connected:
                await self._listen()

