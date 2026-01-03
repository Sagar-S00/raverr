"""
Rave Bot Module
Discord-like command bot for Rave WebSocket rooms

Usage:
    from rave_api.bot import RaveBot
    
    bot = RaveBot(
        server="r13--sn-b8u7h2.hefio.com",
        room_id="40b73841-e6eb-4c0c-95de-b4fd57ac96ef",
        peer_id="122414287_3e8e7a1a3514465ea7d5933cf855d22a",
        auth_token="your_token",
        command_prefix="!",
        debug=False
    )
    
    # Add custom commands
    @bot.command("hello")
    async def hello_command(ctx):
        await ctx.reply("Hello! 👋")
    
    # Run bot
    await bot.run()
"""

import asyncio
import json
import logging
from typing import Dict, Callable, Optional, Any, List, Set
import time

from ..websocket import RaveWebSocketClient
from .context import CommandContext
from ..utils.helpers import get_users_list, leave_mesh

logger = logging.getLogger(__name__)


class RaveBot:
    """Discord-like command bot for Rave rooms"""
    
    def __init__(
        self,
        server: str,
        room_id: str,
        peer_id: str,
        auth_token: str = "",
        device_id: str = "",
        command_prefix: str = "!",
        debug: bool = False
    ):
        """
        Initialize Rave Bot
        
        Args:
            server: WebSocket server hostname
            room_id: Mesh room ID
            peer_id: Peer ID (required)
            auth_token: Bearer token for authentication
            device_id: Device ID for API operations
            command_prefix: Prefix for commands (default: "!"). Can be a string or list of strings (e.g., ["!", "?", "~", "+"])
            debug: Enable debug logging (default: False)
        """
        self.server = server
        self.room_id = room_id
        self.peer_id = peer_id
        self.auth_token = auth_token
        self.device_id = device_id
        # Support multiple prefixes - convert string to list if needed
        if isinstance(command_prefix, str):
            self.command_prefixes = [command_prefix]
        else:
            self.command_prefixes = list(command_prefix) if command_prefix else ["!"]
        # Keep single prefix for backward compatibility
        self.command_prefix = self.command_prefixes[0] if self.command_prefixes else "!"
        self.debug = debug
        
        # Extract bot's user ID from peer_id (format: {userId}_{uuid})
        try:
            self.bot_user_id = int(peer_id.split('_')[0])
        except (ValueError, IndexError):
            self.bot_user_id = None
        
        # Command registry
        self.commands: Dict[str, Callable] = {}
        
        # Event registry (event_name -> list of handlers)
        self.events: Dict[str, List[Callable]] = {}
        
        # WebSocket client
        self.client: Optional[RaveWebSocketClient] = None
        
        # Flag to prevent processing kicked notification multiple times
        self._kicked_processed = False
        
        # Track current users (set of user IDs)
        self.current_user_ids: Set[int] = set()
        
        # Cache user display names per mesh (user_id -> display_name)
        self.user_name_cache: Dict[str, Dict[int, str]] = {}  # mesh_id -> {user_id: display_name}
        
        # Track bot's sent message IDs to detect replies
        self.bot_message_ids: Set[str] = set()
        # Also track recent message content to match replies (fallback if server changes IDs)
        self.recent_bot_messages: List[Dict[str, Any]] = []  # Store last 50 messages with content and IDs
        
        # Auto-leave when last user (default: True)
        self.auto_leave_when_last = True
        
        # Flag to track if bot left because it was the last user
        self.left_because_last_user = False
        
        # Register default commands
        self._register_default_commands()
    
    def _register_default_commands(self):
        """Register default commands"""
        
        @self.command("help")
        async def help_command(ctx):
            """Show available commands"""
            commands_list = []
            for cmd_name, cmd_func in self.commands.items():
                doc = cmd_func.__doc__ or "No description"
                # Show all prefixes for each command
                prefix_examples = " / ".join([f"`{prefix}{cmd_name}`" for prefix in self.command_prefixes])
                commands_list.append(f"{prefix_examples} - {doc}")
            
            prefixes_str = ", ".join(self.command_prefixes)
            help_text = f"**Available Commands:** (prefixes: {prefixes_str})\n" + "\n".join(commands_list)
            await ctx.reply(help_text)
        
        @self.command("ping")
        async def ping_command(ctx):
            """Check if bot is alive"""
            await ctx.reply("Pong! 🏓")
        
        @self.command("info")
        async def info_command(ctx):
            """Show bot information"""
            info = f"**Bot Info:**\n"
            info += f"Server: `{self.server}`\n"
            info += f"Room ID: `{self.room_id[:8]}...`\n"
            info += f"Commands: `{len(self.commands)}`"
            await ctx.reply(info)
    
    def command(self, name: str):
        """
        Decorator to register a command
        
        Usage:
            @bot.command("hello")
            async def hello_command(ctx):
                await ctx.reply("Hello!")
        """
        def decorator(func: Callable):
            self.commands[name.lower()] = func
            return func
        return decorator
    
    def event(self, name: str):
        """
        Decorator to register an event handler
        
        Usage:
            @bot.event("on_user_join")
            async def on_user_join_handler(user_info):
                print(f"User joined: {user_info.get('displayName')}")
        """
        def decorator(func: Callable):
            event_name = name.lower()
            if event_name not in self.events:
                self.events[event_name] = []
            self.events[event_name].append(func)
            return func
        return decorator
    
    async def _dispatch_event(self, event_name: str, *args, **kwargs):
        """Dispatch an event to all registered handlers"""
        event_name = event_name.lower()
        if event_name in self.events:
            for handler in self.events[event_name]:
                try:
                    if asyncio.iscoroutinefunction(handler):
                        await handler(*args, **kwargs)
                    else:
                        handler(*args, **kwargs)
                except Exception as e:
                    logger.error(f"Error in event handler {event_name}: {e}", exc_info=True)
    
    async def send_message(
        self,
        text: str,
        reply_to: Optional[str] = None,
        media: Optional[List[Dict[str, Any]]] = None
    ):
        """
        Send a chat message
        
        Args:
            text: Message text to send
            reply_to: Optional message ID to reply to
            media: Optional list of media items to include in message.
                   Format: [{"url": "...", "mime": "...", "isExplicit": False, "aspectRatio": "...", "thumbnailUrl": "..."}, ...]
        """
        if self.client:
            # Send message and get the ID we sent
            sent_message_id = await self.client.send_chat_message(text, reply_to=reply_to, media=media)
            # Track the message ID we sent immediately
            if sent_message_id:
                self.bot_message_ids.add(sent_message_id)
                # Also track message content for fallback matching
                self.recent_bot_messages.append({
                    "id": sent_message_id,
                    "content": text,
                    "timestamp": time.time()
                })
                # Keep only last 50 messages
                if len(self.recent_bot_messages) > 50:
                    self.recent_bot_messages.pop(0)
            # Note: We'll also track the server's assigned ID when we receive our own message back
            return sent_message_id
        return None
    
    def _parse_command(self, message: str) -> Optional[tuple]:
        """
        Parse a command from a message
        
        Returns:
            (command_name, args) or None if not a command
        """
        # Check if message starts with any of the command prefixes
        matched_prefix = None
        for prefix in self.command_prefixes:
            if message.startswith(prefix):
                matched_prefix = prefix
                break
        
        if not matched_prefix:
            return None
        
        # Remove prefix and split
        content = message[len(matched_prefix):].strip()
        if not content:
            return None
        
        # Split command and args
        parts = content.split()
        command = parts[0].lower()
        args = parts[1:] if len(parts) > 1 else []
        
        return (command, args)
    
    def _handle_message(self, data: Dict[str, Any]):
        """Handle incoming WebSocket messages (synchronous wrapper)"""
        # Schedule async handler as a task using the stored event loop
        if hasattr(self, '_event_loop'):
            self._event_loop.create_task(self._handle_message_async(data))
        else:
            # Fallback: try to get current event loop
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    loop.create_task(self._handle_message_async(data))
            except RuntimeError:
                logger.error("No event loop available for handling message")
    
    async def _handle_message_async(self, data: Dict[str, Any]):
        """Handle incoming WebSocket messages (async implementation)"""
        try:
            # Handle kicked notification
            if data.get("notification") and data.get("method") == "kicked":
                # Prevent processing the same kicked notification multiple times
                if self._kicked_processed:
                    return
                self._kicked_processed = True
                if hasattr(self, 'manager') and self.manager:
                    mesh_id = self.room_id
                    if mesh_id in self.manager.bots:
                        bot_info = self.manager.bots[mesh_id]
                        bot_info.kicked = True
                await self._dispatch_event("on_kicked", {})
                if self.client:
                    await self.client.disconnect(code=4003, reason="kicked")
                return
            
            # Handle stateMessage notifications (user join/leave events)
            # Format: {"notification":true,"method":"stateMessage","data":{"message":"{...json...}"}}
            if data.get("notification") and data.get("method") == "stateMessage":
                message_data = data.get("data", {})
                message_str = message_data.get("message", "")
                if message_str:
                    try:
                        state_data = json.loads(message_str)
                        if "users" in state_data and "mesh_state" in state_data:
                            await self._handle_user_state_update(state_data)
                    except ValueError as e:
                        # JSONDecodeError is a subclass of ValueError
                        logger.error(f"Error parsing stateMessage: {e}", exc_info=True)
                    except Exception as e:
                        logger.error(f"Error parsing stateMessage: {e}", exc_info=True)
            
            # Check if it's a chat message notification
            if data.get("notification") and data.get("method") == "chatMessage":
                message_data = data.get("data", {})
                chat_text = message_data.get("chat", "")
                sender = message_data.get("from", "")
                message_id = message_data.get("id", "")
                
                # If message is from bot, track its message ID for reply detection
                if sender == self.peer_id:
                    if message_id:
                        # Track the server's assigned message ID (might be different from what we sent)
                        self.bot_message_ids.add(message_id)
                        # Also match this received ID with any recent sent messages by content
                        # This helps if server assigns different ID
                        for msg in self.recent_bot_messages:
                            if msg["content"] == chat_text and msg["id"] != message_id:
                                # Server assigned different ID - map it
                                self.bot_message_ids.add(message_id)
                                # If this message has video_info, also update video_info_map with server-assigned ID
                                if 'video_info' in msg and hasattr(self, 'video_info_map'):
                                    self.video_info_map[message_id] = msg['video_info']
                                break
                    return
                
                # Parse command
                parsed = self._parse_command(chat_text)
                if parsed:
                    command_name, args = parsed
                    
                    # Check if command exists
                    if command_name in self.commands:
                        # Create context
                        ctx = CommandContext(self, data, command_name, args)
                        
                        # Execute command
                        try:
                            await self.commands[command_name](ctx)
                        except Exception as e:
                            logger.error(f"Error executing command {command_name}: {e}", exc_info=True)
                            await ctx.reply(f"❌ Error executing command: {str(e)}")
                else:
                    # Not a command - fire on_message event
                    # Extract user ID from sender peer_id (format: {userId}_{uuid})
                    try:
                        user_id = int(sender.split('_')[0]) if sender else None
                    except (ValueError, IndexError):
                        user_id = None
                    
                    # Get user display name from cache or fetch
                    user_name = await self._get_user_display_name(user_id)
                    
                    # Extract reply and mentions info
                    reply_to_message_id = message_data.get("reply")
                    user_metas = message_data.get("user_metas", [])
                    
                    # Check if bot is mentioned (user_metas contains bot's user ID)
                    is_mentioned = False
                    if self.bot_user_id and user_metas:
                        is_mentioned = any(
                            meta.get("id") == self.bot_user_id 
                            for meta in user_metas 
                            if isinstance(meta, dict)
                        )
                    
                    # Check if reply is to a bot message
                    is_reply_to_bot = False
                    if reply_to_message_id:
                        if reply_to_message_id in self.bot_message_ids:
                            is_reply_to_bot = True
                            if self.debug:
                                logger.debug(f"Reply to bot confirmed via message ID: {reply_to_message_id}")
                        else:
                            # Fallback: If we recently sent a message (within last 30 seconds), 
                            # assume any reply might be to our message (server might use different ID)
                            current_time = time.time()
                            recent_messages = [msg for msg in self.recent_bot_messages 
                                             if current_time - msg.get("timestamp", 0) < 30]
                            if recent_messages:
                                # We sent a message recently, likely this reply is to us
                                is_reply_to_bot = True
                                logger.info(f"Assuming reply to bot (recent message sent, server ID mismatch: {reply_to_message_id})")
                            elif self.debug:
                                # Debug: log what message IDs we're tracking
                                logger.debug(f"Reply to message {reply_to_message_id} not in sent IDs")
                                logger.debug(f"Tracked bot message IDs (first 10): {list(self.bot_message_ids)[:10]}")
                                logger.debug(f"Total tracked message IDs: {len(self.bot_message_ids)}")
                                logger.debug(f"Recent bot messages: {len(self.recent_bot_messages)}")
                    
                    # Prepare message info for event
                    message_info = {
                        "message": chat_text,
                        "sender_peer_id": sender,
                        "sender_user_id": user_id,
                        "sender_name": user_name,
                        "message_id": message_id,
                        "mesh_id": self.room_id,
                        "reply_to": reply_to_message_id,  # Message ID this is replying to
                        "is_reply": reply_to_message_id is not None,  # Whether this is a reply
                        "is_reply_to_bot": is_reply_to_bot,  # Whether reply is to bot's message
                        "is_mentioned": is_mentioned,  # Whether bot is mentioned/tagged
                        "user_metas": user_metas,  # List of mentioned users
                        "raw_data": message_data,
                        "bot": self  # Include bot instance for sending replies
                    }
                    
                    # Fire on_message event
                    await self._dispatch_event("on_message", message_info)
        
        except Exception as e:
            logger.error(f"Error handling message: {e}", exc_info=True)
    
    async def _handle_user_state_update(self, data: Dict[str, Any]):
        """Handle user state updates (join/leave detection)"""
        try:
            users = data.get("users", [])
            current_ids = {user.get("user_id") for user in users if user.get("user_id") is not None}
            
            # Detect joins (new user IDs not in previous set)
            joined_ids = current_ids - self.current_user_ids
            
            # Detect leaves (user IDs in previous set but not in current)
            left_ids = self.current_user_ids - current_ids
            
            # Update current user IDs
            self.current_user_ids = current_ids
            
            # Handle joins
            if joined_ids:
                await self._handle_users_joined(list(joined_ids))
            
            # Handle leaves
            if left_ids:
                await self._handle_users_left(list(left_ids))
                
        except Exception as e:
            logger.error(f"Error handling user state update: {e}", exc_info=True)
    
    async def _get_user_display_name(self, user_id: Optional[int]) -> str:
        """
        Get user display name, using cache if available, otherwise fetch from API.
        
        Args:
            user_id: User ID to get display name for
            
        Returns:
            Display name or fallback string
        """
        if user_id is None:
            return "Unknown User"
        
        # Initialize cache for this mesh if needed
        if self.room_id not in self.user_name_cache:
            self.user_name_cache[self.room_id] = {}
        
        # Check cache first
        if user_id in self.user_name_cache[self.room_id]:
            return self.user_name_cache[self.room_id][user_id]
        
        # Fetch from API
        try:
            response = get_users_list(ids=[user_id], device_id=self.device_id, include_online=True)
            users_data = response.get("data", [])
            
            if users_data:
                user_info = users_data[0]
                display_name = user_info.get('displayName') or user_info.get('handle') or f"User {user_id}"
                # Cache it
                self.user_name_cache[self.room_id][user_id] = display_name
                return display_name
        except Exception as e:
            logger.error(f"Error fetching user name for {user_id}: {e}", exc_info=True)
        
        # Fallback
        fallback_name = f"User {user_id}"
        self.user_name_cache[self.room_id][user_id] = fallback_name
        return fallback_name
    
    async def _handle_users_joined(self, user_ids: List[int]):
        """Handle user joins - fetch user details and fire event"""
        if not user_ids:
            return
        
        try:
            # Get user details
            response = get_users_list(ids=user_ids, device_id=self.device_id, include_online=True)
            users_data = response.get("data", [])
            
            # Initialize cache for this mesh if needed
            if self.room_id not in self.user_name_cache:
                self.user_name_cache[self.room_id] = {}
            
            # Fire event for each joined user and cache names
            for user_info in users_data:
                user_id = user_info.get('id')
                if user_id:
                    display_name = user_info.get('displayName') or user_info.get('handle') or f"User {user_id}"
                    # Cache the name
                    self.user_name_cache[self.room_id][user_id] = display_name
                
                await self._dispatch_event("on_user_join", user_info)
        
        except Exception as e:
            logger.error(f"Error fetching user details for joined users: {e}", exc_info=True)
    
    async def _handle_users_left(self, user_ids: List[int]):
        """Handle user leaves - fetch user details and fire event"""
        if not user_ids:
            return
        
        try:
            # Get user details
            response = get_users_list(ids=user_ids, device_id=self.device_id, include_online=True)
            users_data = response.get("data", [])
            
            # Fire event for each left user
            for user_info in users_data:
                await self._dispatch_event("on_user_left", user_info)
            
            # Check if bot is the last user remaining
            if self.auto_leave_when_last and self.bot_user_id is not None:
                # Check if only the bot remains
                remaining_users = self.current_user_ids.copy()
                if len(remaining_users) == 1 and self.bot_user_id in remaining_users:
                    self.left_because_last_user = True
                    await self._leave_mesh()
        
        except Exception as e:
            logger.error(f"Error fetching user details for left users: {e}", exc_info=True)
    
    async def _leave_mesh(self):
        """Leave the mesh and disconnect"""
        try:
            # Call leave mesh API
            from ..api import RaveAPIClient
            
            api_client = RaveAPIClient(auth_token=self.auth_token)
            leave_mesh(self.room_id, self.device_id, api_client=api_client)
            
        except Exception as e:
            logger.error(f"Error leaving mesh via API: {e}", exc_info=True)
        
        # Disconnect websocket
        if self.client:
            try:
                await self.client.disconnect()
            except Exception as e:
                logger.error(f"Error disconnecting from mesh: {e}", exc_info=True)
    
    async def run(self):
        """Run the bot"""
        # Store event loop for use in synchronous callback
        self._event_loop = asyncio.get_event_loop()
        
        # Track if we've sent the hello message
        self._hello_sent = False
        
        # Initialize WebSocket client
        def on_connected_callback():
            """Callback when bot connects - fire on_connected event"""
            # Fire on_connected event (handler can send hello message)
            # Schedule async event dispatch
            if hasattr(self, '_event_loop'):
                self._event_loop.create_task(self._dispatch_event("on_connected", self))
            else:
                try:
                    loop = asyncio.get_event_loop()
                    if loop.is_running():
                        loop.create_task(self._dispatch_event("on_connected", self))
                except RuntimeError:
                    pass
        
        self.client = RaveWebSocketClient(
            server=self.server,
            room_id=self.room_id,
            peer_id=self.peer_id,
            auth_token=self.auth_token,
            debug=self.debug,
            on_message=self._handle_message,
            on_connected=on_connected_callback,
            on_disconnected=lambda: None,
            on_error=lambda e: logger.error(f"❌ Bot error: {e}")
        )
        
        try:
            # Connect
            connected = await self.client.connect()
            if not connected:
                logger.error("Failed to connect bot")
                return
            
            # Keep running - wait for the listen task that was started in connect()
            if self.client.listen_task:
                await self.client.listen_task
        
        except KeyboardInterrupt:
            pass
        except Exception as e:
            logger.error(f"Bot error: {e}", exc_info=True)
        finally:
            if self.client:
                await self.client.disconnect()

