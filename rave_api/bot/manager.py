"""
Rave Bot Manager Module
Manages multiple RaveBot instances for multiple meshes
"""

import asyncio
import logging
from typing import Dict, Callable, Optional, Any, List
from enum import Enum

from .bot import RaveBot
from ..utils.helpers import get_invited_meshes, get_mesh_info
from ..api import RaveAPIClient

logger = logging.getLogger(__name__)


class BotState(Enum):
    """Bot connection state"""
    INITIALIZING = "initializing"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    DISCONNECTED = "disconnected"
    RETRYING = "retrying"
    FAILED = "failed"
    STOPPED = "stopped"


class BotInfo:
    """Information about a bot instance"""
    def __init__(self, mesh_id: str, mesh_data: Dict[str, Any]):
        self.mesh_id = mesh_id
        self.mesh_data = mesh_data
        self.bot: Optional[RaveBot] = None
        self.state = BotState.INITIALIZING
        self.retry_count = 0
        self.retry_task: Optional[asyncio.Task] = None
        self.run_task: Optional[asyncio.Task] = None
        self.monitor_task: Optional[asyncio.Task] = None
        self.kicked = False


class BotManager:
    """
    Manages multiple RaveBot instances for multiple meshes
    
    Automatically fetches invited meshes and creates bot instances for each.
    Handles connection failures with automatic retry.
    """
    
    def __init__(
        self,
        device_id: str,
        peer_id: str,
        auth_token: str = "",
        command_prefix: str = "!",
        debug: bool = False,
        api_client: Optional[RaveAPIClient] = None,
        max_retries: int = 10,
        retry_initial_backoff: float = 1.0,
        retry_max_backoff: float = 60.0,
        discovery_interval: float = 60.0,
        mesh_mode: str = "invited"
    ):
        """
        Initialize Bot Manager
        
        Args:
            device_id: Device ID (required)
            peer_id: Peer ID (required, format: {userId}_{uuid})
            auth_token: Bearer token for authentication
            command_prefix: Prefix for commands (default: "!")
            debug: Enable debug logging (default: False)
            api_client: Optional API client instance
            max_retries: Maximum retry attempts per bot (default: 10)
            retry_initial_backoff: Initial retry backoff in seconds (default: 1.0)
            retry_max_backoff: Maximum retry backoff in seconds (default: 60.0)
            discovery_interval: Interval in seconds to check for new/removed meshes (default: 60.0)
            mesh_mode: "invited" for only invited meshes, "all" for public + friends + invited (default: "invited")
        """
        self.device_id = device_id
        self.peer_id = peer_id
        self.auth_token = auth_token
        self.command_prefix = command_prefix
        self.debug = debug
        self.api_client = api_client or RaveAPIClient(auth_token=auth_token)
        self.max_retries = max_retries
        self.retry_initial_backoff = retry_initial_backoff
        self.retry_max_backoff = retry_max_backoff
        self.discovery_interval = discovery_interval
        self.mesh_mode = mesh_mode
        
        # Bot registry: mesh_id -> BotInfo
        self.bots: Dict[str, BotInfo] = {}
        
        # Global commands and events (applied to all bots)
        self.global_commands: Dict[str, Callable] = {}
        self.global_events: Dict[str, List[Callable]] = {}
        
        # Running state
        self.is_running = False
        self._shutdown_event = asyncio.Event()
        self._discovery_task: Optional[asyncio.Task] = None
        self._empty_check_task: Optional[asyncio.Task] = None
        self._limit = 20
        self._lang = "en"
    
    async def fetch_meshes(self, limit: int = 20, lang: str = "en") -> List[Dict[str, Any]]:
        """
        Fetch meshes from API based on mesh_mode
        
        Args:
            limit: Maximum number of meshes to fetch (default: 20)
            lang: Language code (default: "en")
            
        Returns:
            List of mesh data dictionaries
        """
        try:
            from ..utils.helpers import get_meshes
            response = get_meshes(
                device_id=self.device_id,
                mode=self.mesh_mode,
                limit=limit,
                lang=lang,
                api_client=self.api_client
            )
            meshes_data = response.get("data", [])
            return meshes_data
        except Exception as e:
            error_msg = str(e).lower()
            error_type = type(e).__name__
            is_network = ("getaddrinfo" in error_msg or "name resolution" in error_msg or 
                         "dns" in error_msg or "ConnectionError" in error_type or 
                         "connection" in error_msg)
            
            # Log network errors more concisely
            if is_network:
                logger.error(f"Failed to fetch meshes (network error): {str(e)[:200]}")
            else:
                logger.error(f"Failed to fetch meshes: {e}", exc_info=True)
            return []
    
    async def fetch_invited_meshes(self, limit: int = 20, lang: str = "en") -> List[Dict[str, Any]]:
        """Deprecated: Use fetch_meshes instead"""
        return await self.fetch_meshes(limit, lang)
    
    def _create_bot_for_mesh(self, mesh_id: str, server: str, mesh_data: Dict[str, Any]) -> RaveBot:
        """
        Create a RaveBot instance for a mesh
        
        Args:
            mesh_id: Mesh ID
            server: WebSocket server hostname
            mesh_data: Full mesh data dictionary
            
        Returns:
            RaveBot instance
        """
        bot = RaveBot(
            server=server,
            room_id=mesh_id,
            peer_id=self.peer_id,
            auth_token=self.auth_token,
            device_id=self.device_id,
            command_prefix=self.command_prefix,
            debug=self.debug
        )
        
        # Register global commands
        for cmd_name, cmd_func in self.global_commands.items():
            bot.commands[cmd_name] = cmd_func
        
        # Register global events
        for event_name, handlers in self.global_events.items():
            for handler in handlers:
                if event_name not in bot.events:
                    bot.events[event_name] = []
                bot.events[event_name].append(handler)
        
        return bot
    
    async def _start_bot(self, bot_info: BotInfo):
        """
        Start a bot instance and handle connection lifecycle
        
        Args:
            bot_info: BotInfo instance to start
        """
        mesh_id = bot_info.mesh_id
        mesh_data = bot_info.mesh_data
        
        try:
            # Get mesh info to extract server
            mesh_info = get_mesh_info(mesh_id, api_client=self.api_client)
            server = mesh_info.get("server")
            
            if not server:
                logger.error(f"No server found for mesh {mesh_id}")
                bot_info.state = BotState.FAILED
                return
            
            # Create bot instance
            bot_info.bot = self._create_bot_for_mesh(mesh_id, server, mesh_data)
            bot_info.state = BotState.CONNECTING
            
            # Start connection monitoring task
            bot_info.monitor_task = asyncio.create_task(self._monitor_bot_connection(bot_info))
            
            # Run bot (this will connect and listen)
            bot_info.run_task = asyncio.create_task(self._run_bot_with_retry(bot_info))
            
        except Exception as e:
            logger.error(f"Failed to start bot for mesh {mesh_id}: {e}", exc_info=True)
            bot_info.state = BotState.FAILED
    
    async def _monitor_bot_connection(self, bot_info: BotInfo):
        """
        Monitor bot connection state
        
        Args:
            bot_info: BotInfo instance to monitor
        """
        mesh_id = bot_info.mesh_id
        
        while not self._shutdown_event.is_set():
            try:
                await asyncio.sleep(2.0)  # Check every 2 seconds
                
                if bot_info.bot and bot_info.bot.client:
                    if bot_info.bot.client.is_connected:
                        if bot_info.state != BotState.CONNECTED:
                            bot_info.state = BotState.CONNECTED
                            bot_info.retry_count = 0  # Reset retry count on successful connection
                            pass
                    elif bot_info.state == BotState.CONNECTED:
                        # Was connected but now disconnected
                        bot_info.state = BotState.DISCONNECTED
                        
                        # If bot disconnected because it was the last user, remove it from registry
                        # (don't retry in this case)
                        if (not bot_info.bot.client.is_connected and 
                            bot_info.bot.left_because_last_user):
                            # Mark as stopped so it won't retry
                            bot_info.state = BotState.STOPPED
                            # Cancel run task to stop retries
                            if bot_info.run_task:
                                bot_info.run_task.cancel()
                            # Remove from registry
                            if mesh_id in self.bots:
                                del self.bots[mesh_id]
                            break
            except asyncio.CancelledError:
                break
            except Exception as e:
                pass
    
    async def _run_bot_with_retry(self, bot_info: BotInfo):
        """
        Run a bot with automatic retry on failure
        
        Args:
            bot_info: BotInfo instance to run
        """
        mesh_id = bot_info.mesh_id
        
        while not self._shutdown_event.is_set() and bot_info.retry_count < self.max_retries:
            try:
                if bot_info.bot is None:
                    # Need to recreate bot
                    mesh_data = bot_info.mesh_data
                    mesh_info = get_mesh_info(mesh_id, api_client=self.api_client)
                    server = mesh_info.get("server")
                    
                    if not server:
                        logger.error(f"No server found for mesh {mesh_id}")
                        bot_info.state = BotState.FAILED
                        break
                    
                    bot_info.bot = self._create_bot_for_mesh(mesh_id, server, mesh_data)
                    bot_info.state = BotState.CONNECTING
                    
                    # Start connection monitoring if not already running
                    if not bot_info.monitor_task or bot_info.monitor_task.done():
                        bot_info.monitor_task = asyncio.create_task(self._monitor_bot_connection(bot_info))
                
                bot_info.state = BotState.CONNECTING
                
                # Run bot (this blocks until disconnect)
                await bot_info.bot.run()
                
                # If we get here, bot disconnected
                bot_info.state = BotState.DISCONNECTED
                
                # Check if bot was kicked or left because it was the last user - don't retry in these cases
                if bot_info.kicked or bot_info.bot.left_because_last_user:
                    bot_info.state = BotState.STOPPED
                    # Remove from registry
                    if mesh_id in self.bots:
                        del self.bots[mesh_id]
                    break
                
                # Check if we should retry
                if self._shutdown_event.is_set():
                    break
                
                if bot_info.retry_count >= self.max_retries:
                    logger.error(f"Max retries reached for mesh {mesh_id}")
                    bot_info.state = BotState.FAILED
                    break
                
                # Schedule retry
                bot_info.state = BotState.RETRYING
                bot_info.retry_count += 1
                backoff = min(
                    self.retry_initial_backoff * (1.5 ** bot_info.retry_count),
                    self.retry_max_backoff
                )
                
                await asyncio.sleep(backoff)
                
                # Clean up old bot
                if bot_info.bot:
                    try:
                        if bot_info.bot.client:
                            await bot_info.bot.client.disconnect()
                    except:
                        pass
                    bot_info.bot = None
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                error_msg = str(e).lower()
                error_type = type(e).__name__
                
                # Detect different types of network errors
                is_timeout = "timeout" in error_msg or "timed out" in error_msg
                is_dns = "getaddrinfo" in error_msg or "name resolution" in error_msg or "dns" in error_msg or "NameResolutionError" in error_type
                is_connection = "ConnectionError" in error_type or "connection" in error_msg
                is_network = is_dns or is_connection or "network" in error_msg
                
                # Log network errors more concisely (without full traceback)
                if is_network:
                    logger.error(f"Network error for mesh {mesh_id}: {str(e)[:200]}")
                else:
                    logger.error(f"Error running bot for mesh {mesh_id}: {e}", exc_info=True)
                
                bot_info.state = BotState.DISCONNECTED
                
                if bot_info.retry_count >= self.max_retries:
                    bot_info.state = BotState.FAILED
                    break
                
                # Schedule retry
                bot_info.state = BotState.RETRYING
                bot_info.retry_count += 1
                
                # Use longer backoff for network errors (DNS/connection issues take longer to recover)
                if is_dns:
                    # DNS errors need much longer backoff - network is likely down
                    base_backoff = self.retry_initial_backoff * 5
                elif is_timeout or is_connection:
                    # Timeout/connection errors need longer backoff
                    base_backoff = self.retry_initial_backoff * 2
                else:
                    base_backoff = self.retry_initial_backoff
                
                backoff = min(
                    base_backoff * (1.5 ** bot_info.retry_count),
                    self.retry_max_backoff
                )
                
                await asyncio.sleep(backoff)
                
                # Clean up old bot
                if bot_info.bot:
                    try:
                        if bot_info.bot.client:
                            await bot_info.bot.client.disconnect()
                    except:
                        pass
                    bot_info.bot = None
        
        if bot_info.retry_count >= self.max_retries:
            bot_info.state = BotState.FAILED
            logger.error(f"Failed to connect to mesh {mesh_id} after {self.max_retries} attempts")
        
        # Cancel monitor task
        if bot_info.monitor_task:
            bot_info.monitor_task.cancel()
            try:
                await bot_info.monitor_task
            except asyncio.CancelledError:
                pass
    
    async def _stop_bot(self, bot_info: BotInfo):
        """
        Stop and remove a bot instance
        
        Args:
            bot_info: BotInfo instance to stop
        """
        mesh_id = bot_info.mesh_id
        
        
        # Cancel monitor task
        if bot_info.monitor_task:
            bot_info.monitor_task.cancel()
            try:
                await bot_info.monitor_task
            except asyncio.CancelledError:
                pass
        
        # Cancel run task
        if bot_info.run_task:
            bot_info.run_task.cancel()
            try:
                await bot_info.run_task
            except asyncio.CancelledError:
                pass
        
        # Disconnect bot
        if bot_info.bot and bot_info.bot.client:
            try:
                await bot_info.bot.client.disconnect()
            except:
                pass
        
        bot_info.state = BotState.STOPPED
    
    async def _sync_meshes(self, meshes_data: List[Dict[str, Any]]):
        """
        Sync bot instances with current invited meshes
        
        Starts new bots for new meshes and stops bots for removed meshes.
        
        Args:
            meshes_data: List of current invited mesh data
        """
        # Extract mesh IDs from current invited meshes
        current_mesh_ids = set()
        mesh_data_map = {}
        
        for mesh_entry in meshes_data:
            
            mesh = mesh_entry.get("mesh", {})
            mesh_id = mesh.get("id")
            if mesh_id:
                current_mesh_ids.add(mesh_id)
                mesh_data_map[mesh_id] = mesh_entry
        
        # Find meshes that need to be added (new invites)
        existing_mesh_ids = set(self.bots.keys())
        new_mesh_ids = current_mesh_ids - existing_mesh_ids
        
        # Find meshes that need to be removed (no longer invited)
        removed_mesh_ids = existing_mesh_ids - current_mesh_ids
        
        # Start new bots with rate limiting (delay between each start)
        for idx, mesh_id in enumerate(new_mesh_ids):
            if mesh_id in mesh_data_map:
                bot_info = BotInfo(mesh_id=mesh_id, mesh_data=mesh_data_map[mesh_id])
                self.bots[mesh_id] = bot_info
                # Add delay between starting bots to avoid connection floods
                if idx > 0:
                    await asyncio.sleep(0.5)  # 500ms delay between each bot start
                asyncio.create_task(self._start_bot(bot_info))
        
        # Stop removed bots
        for mesh_id in removed_mesh_ids:
            bot_info = self.bots.get(mesh_id)
            if bot_info:
                await self._stop_bot(bot_info)
                del self.bots[mesh_id]
        
        if new_mesh_ids or removed_mesh_ids:
            pass
    
    async def _discovery_loop(self):
        """
        Periodic discovery loop that checks for new/removed meshes every minute
        """
        # Wait for initial sync to complete before starting periodic checks
        await asyncio.sleep(self.discovery_interval)
        
        while not self._shutdown_event.is_set():
            try:
                if self._shutdown_event.is_set():
                    break
                
                
                # Fetch current invited meshes
                meshes_data = await self.fetch_invited_meshes(limit=self._limit, lang=self._lang)
                
                # Sync bots with current meshes
                await self._sync_meshes(meshes_data)
                
                # Wait for next interval
                await asyncio.sleep(self.discovery_interval)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in discovery loop: {e}", exc_info=True)
                # Continue even if there's an error, but wait before retrying
                await asyncio.sleep(self.discovery_interval)
    
    async def _empty_mesh_check_loop(self):
        """Periodic check to leave empty meshes (every 3 minutes)"""
        await asyncio.sleep(180)  # Wait 3 minutes before first check
        
        while not self._shutdown_event.is_set():
            try:
                if self._shutdown_event.is_set():
                    break
                
                for mesh_id, bot_info in list(self.bots.items()):
                    if bot_info.kicked:
                        continue
                    
                    if bot_info.bot and bot_info.state == BotState.CONNECTED:
                        try:
                            mesh_info = get_mesh_info(mesh_id, api_client=self.api_client)
                            users = mesh_info.get("users", [])
                            
                            if len(users) == 1:
                                user = users[0]
                                user_id = user.get("id") if isinstance(user, dict) else str(user)
                                peer_id_parts = self.peer_id.split("_")
                                bot_user_id = peer_id_parts[0] if len(peer_id_parts) > 0 else None
                                
                                if str(user_id) == str(bot_user_id):
                                    from ..utils.helpers import leave_mesh
                                    leave_mesh(mesh_id, self.device_id, self.api_client)
                                    await self._stop_bot(bot_info)
                        except Exception:
                            pass
                
                await asyncio.sleep(180)  # Check every 3 minutes
                
            except asyncio.CancelledError:
                break
            except Exception:
                await asyncio.sleep(180)
    
    async def start(self, limit: int = 20, lang: str = "en"):
        """
        Start the bot manager
        
        Fetches invited meshes and starts bot instances for each.
        Also starts periodic discovery task.
        
        Args:
            limit: Maximum number of meshes to fetch (default: 20)
            lang: Language code (default: "en")
        """
        if self.is_running:
            return
        
        self.is_running = True
        self._shutdown_event.clear()
        self._limit = limit
        self._lang = lang
        
        
        # Fetch invited meshes
        meshes_data = await self.fetch_invited_meshes(limit=limit, lang=lang)
        
        # Sync bots with initial meshes
        await self._sync_meshes(meshes_data)
        
        # Start periodic discovery task
        self._discovery_task = asyncio.create_task(self._discovery_loop())
        
        # Start empty mesh check task
        self._empty_check_task = asyncio.create_task(self._empty_mesh_check_loop())
        
    
    async def stop(self):
        """Stop all bot instances"""
        if not self.is_running:
            return
        
        self.is_running = False
        self._shutdown_event.set()
        
        # Stop discovery task
        if self._discovery_task:
            self._discovery_task.cancel()
            try:
                await self._discovery_task
            except asyncio.CancelledError:
                pass
        
        # Stop empty check task
        if self._empty_check_task:
            self._empty_check_task.cancel()
            try:
                await self._empty_check_task
            except asyncio.CancelledError:
                pass
        
        # Stop all bots
        stop_tasks = []
        for mesh_id, bot_info in list(self.bots.items()):
            await self._stop_bot(bot_info)
        
    
    def command(self, name: str):
        """
        Decorator to register a command for all bots
        
        Usage:
            @manager.command("hello")
            async def hello_command(ctx):
                await ctx.reply("Hello!")
        """
        def decorator(func: Callable):
            self.global_commands[name.lower()] = func
            # Also register for existing bots
            for bot_info in self.bots.values():
                if bot_info.bot:
                    bot_info.bot.commands[name.lower()] = func
            return func
        return decorator
    
    def event(self, name: str):
        """
        Decorator to register an event handler for all bots
        
        Usage:
            @manager.event("on_user_join")
            async def on_user_join_handler(user_info):
                print(f"User joined: {user_info.get('displayName')}")
        """
        def decorator(func: Callable):
            event_name = name.lower()
            if event_name not in self.global_events:
                self.global_events[event_name] = []
            self.global_events[event_name].append(func)
            # Also register for existing bots
            for bot_info in self.bots.values():
                if bot_info.bot:
                    if event_name not in bot_info.bot.events:
                        bot_info.bot.events[event_name] = []
                    bot_info.bot.events[event_name].append(func)
            return func
        return decorator
    
    def get_status(self) -> Dict[str, Any]:
        """
        Get status of all bots
        
        Returns:
            Dictionary with status information
        """
        status = {
            "is_running": self.is_running,
            "total_bots": len(self.bots),
            "bots": {}
        }
        
        for mesh_id, bot_info in self.bots.items():
            status["bots"][mesh_id] = {
                "state": bot_info.state.value,
                "retry_count": bot_info.retry_count,
                "mesh_id": mesh_id
            }
        
        return status
    
    async def run(self, limit: int = 20, lang: str = "en"):
        """
        Run the bot manager (start and wait until stopped)
        
        Args:
            limit: Maximum number of meshes to fetch (default: 20)
            lang: Language code (default: "en")
        """
        await self.start(limit=limit, lang=lang)
        
        try:
            # Wait until shutdown
            await self._shutdown_event.wait()
        except KeyboardInterrupt:
            pass
        finally:
            await self.stop()

