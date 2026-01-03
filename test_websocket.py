"""
Standalone WebSocket Connection Test
Tests WebSocket connection to Rave mesh rooms directly
"""

import asyncio
import json
import logging
import ssl
from urllib.parse import urlencode

import websockets
from websockets.exceptions import ConnectionClosed, InvalidStatus, NegotiationError

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Credentials from mainbot.py
DEVICE_ID = "3e8e7a1a3514465ea7d5933cf855d22a"
AUTH_TOKEN = "318992d9edb53e2ae370c0777e0789be"
PEER_ID = "122414287_3e8e7a1a3514465ea7d5933cf855d22a"


async def get_mesh_info():
    """Get mesh info from API to get server and room_id"""
    from rave_api import RaveAPIClient
    from rave_api.utils.helpers import get_meshes
    
    api_client = RaveAPIClient(auth_token=AUTH_TOKEN)
    
    try:
        # Get invited meshes
        response = get_meshes(
            device_id=DEVICE_ID,
            mode="invited",
            limit=1,
            lang="en",
            api_client=api_client
        )
        print(response)
        
        meshes_data = response.get("data", [])
        
        if not meshes_data:
            logger.error("No invited meshes found")
            return None
        
        mesh_item = meshes_data[0]
        mesh = mesh_item.get("mesh", {})
        
        mesh_id = mesh.get("id")
        server = mesh.get("server")
        room_id = mesh.get("id")  # room_id is usually the same as mesh id
        
        logger.info(f"Found mesh: {mesh_id}")
        logger.info(f"Server: {server}, Room ID: {room_id}")
        
        return {
            "mesh_id": mesh_id,
            "server": server,
            "room_id": room_id
        }
    except Exception as e:
        logger.error(f"Failed to get mesh info: {e}", exc_info=True)
        return None


def build_websocket_url(server: str, room_id: str, peer_id: str) -> str:
    """Build WebSocket URL"""
    params = {
        "roomId": room_id,
        "peerId": peer_id
    }
    query_string = urlencode(params)
    
    # Format: wss://{server}:443/?roomId={roomId}&peerId={peerId}
    if server.startswith("wss://") or server.startswith("ws://"):
        base_url = server
    else:
        base_url = f"wss://{server}"
    
    # Ensure port 443 is specified
    if ":443" not in base_url and not base_url.endswith(":443"):
        if base_url.startswith("wss://"):
            base_url = base_url.replace("wss://", "wss://") + ":443"
        else:
            base_url = base_url + ":443"
    
    url = f"{base_url}/?{query_string}"
    return url


async def test_connection_method(url: str, method_name: str, headers: dict, use_subprotocols: bool = False, use_header_protocol: bool = False):
    """Test a specific connection method"""
    logger.info(f"\n{'='*60}")
    logger.info(f"Testing method: {method_name}")
    logger.info(f"URL: {url}")
    logger.info(f"Headers: {headers}")
    logger.info(f"Use subprotocols parameter: {use_subprotocols}")
    logger.info(f"Use header protocol: {use_header_protocol}")
    logger.info(f"{'='*60}")
    
    # Build headers
    test_headers = headers.copy()
    if use_header_protocol:
        test_headers["Sec-WebSocket-Protocol"] = "protoo"
    
    # Create SSL context
    ssl_context = ssl.create_default_context()
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE
    
    # Build connect kwargs
    connect_kwargs = {
        "ssl": ssl_context,
        "ping_interval": None
    }
    
    if use_subprotocols:
        connect_kwargs["subprotocols"] = ["protoo"]
    
    # Add headers
    try:
        import websockets.version
        WEBSOCKETS_VERSION = tuple(map(int, websockets.version.version.split('.')))
    except (AttributeError, ImportError, ValueError):
        WEBSOCKETS_VERSION = (12, 0, 0)
    
    if WEBSOCKETS_VERSION >= (12, 0, 0):
        connect_kwargs["additional_headers"] = test_headers
    else:
        connect_kwargs["extra_headers"] = test_headers
    
    try:
        logger.info(f"Attempting connection...")
        websocket = await websockets.connect(url, **connect_kwargs)
        logger.info(f"✅ SUCCESS! Connected using method: {method_name}")
        
        # Try to receive a message
        try:
            message = await asyncio.wait_for(websocket.recv(), timeout=5.0)
            logger.info(f"Received message: {message[:200]}")
        except asyncio.TimeoutError:
            logger.info("No message received within 5 seconds (this is OK)")
        except Exception as e:
            logger.warning(f"Error receiving message: {e}")
        
        await websocket.close()
        return True
        
    except NegotiationError as e:
        logger.error(f"❌ NegotiationError: {e}")
        return False
    except InvalidStatus as e:
        status_code = getattr(e, 'status_code', None)
        if status_code is None:
            error_msg = str(e)
            import re
            match = re.search(r'HTTP (\d+)', error_msg)
            if match:
                status_code = int(match.group(1))
        logger.error(f"❌ InvalidStatus (HTTP {status_code}): {e}")
        return False
    except Exception as e:
        logger.error(f"❌ Error: {type(e).__name__} - {e}")
        return False


async def main():
    """Main test function"""
    logger.info("Starting WebSocket connection test...")
    logger.info(f"Device ID: {DEVICE_ID}")
    logger.info(f"Peer ID: {PEER_ID}")
    logger.info(f"Auth Token: {AUTH_TOKEN[:20]}...")
    
    # Get mesh info
    mesh_info = await get_mesh_info()
    if not mesh_info:
        logger.error("Failed to get mesh info. Exiting.")
        return
    
    server = mesh_info["server"]
    room_id = mesh_info["room_id"]
    
    # Build URL
    url = build_websocket_url(server, room_id, PEER_ID)
    logger.info(f"\nWebSocket URL: {url}\n")
    
    # Build base headers
    headers = {
        "API-Version": "4",
        "Authorization": f"Bearer {AUTH_TOKEN}"
    }
    
    # Test different connection methods
    methods = [
        {
            "name": "subprotocols_only",
            "headers": headers,
            "use_subprotocols": True,
            "use_header_protocol": False
        },
        {
            "name": "header_only",
            "headers": headers,
            "use_subprotocols": False,
            "use_header_protocol": True
        },
        {
            "name": "both",
            "headers": headers,
            "use_subprotocols": True,
            "use_header_protocol": True
        },
        {
            "name": "none",
            "headers": headers,
            "use_subprotocols": False,
            "use_header_protocol": False
        }
    ]
    
    success = False
    for method in methods:
        result = await test_connection_method(
            url,
            method["name"],
            method["headers"],
            method["use_subprotocols"],
            method["use_header_protocol"]
        )
        
        if result:
            success = True
            logger.info(f"\n🎉 Connection successful with method: {method['name']}")
            break
        
        # Wait a bit before next attempt
        await asyncio.sleep(2)
    
    if not success:
        logger.error("\n❌ All connection methods failed!")
    else:
        logger.info("\n✅ Test completed successfully!")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("\nTest interrupted by user")
    except Exception as e:
        logger.error(f"Test failed: {e}", exc_info=True)

