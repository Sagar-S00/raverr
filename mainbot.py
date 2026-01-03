"""
Example Multi-Mesh Bot Manager
Demonstrates connecting to all invited meshes and managing multiple bot instances
"""

import asyncio
import logging
from rave_api import BotManager, RaveAPIClient, set_default_api_client
from bot_commands import register_commands
from bot_events import register_events

logging.basicConfig(
    level=logging.ERROR,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


async def main():
    """Main bot manager function"""
    device_id = "3e8e7a1a3514465ea7d5933cf855d22a"
    auth_token = "318992d9edb53e2ae370c0777e0789be"
    peer_id = "122414287_3e8e7a1a3514465ea7d5933cf855d22a"
    
    api_client = RaveAPIClient(auth_token=auth_token)
    set_default_api_client(api_client)
    
    manager = BotManager(
        device_id=device_id,
        peer_id=peer_id,
        auth_token=auth_token,
        command_prefix=["!", "?", "~", "+"],
        debug=False,
        discovery_interval=60.0,
        mesh_mode="invited"  # "invited" or "all"
    )
    
    register_events(manager)
    register_commands(manager)
    
    try:
        await manager.run(limit=20, lang="en")
    except KeyboardInterrupt:
        await manager.stop()
    except Exception as e:
        logger.error(f"Error running bot manager: {e}", exc_info=True)
        await manager.stop()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass

