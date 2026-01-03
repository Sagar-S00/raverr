"""
Example Rave Bot with custom commands
"""

import asyncio
import logging
from rave_api import RaveBot, get_video_id, vote_video, get_mesh_info, RaveAPIClient, set_default_api_client
from youtube_search import search_and_get_video_data
from pprint import pprint

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

async def main():
    """Main bot function"""
    mesh_id = "fec70844-a060-4d35-9e06-b08119bf4d2d"
    auth_token = "318992d9edb53e2ae370c0777e0789be"
    
    # Set up API client for helper functions
    api_client = RaveAPIClient(auth_token=auth_token)
    set_default_api_client(api_client)
    
    try:
        mesh_info = get_mesh_info(mesh_id)
        server = mesh_info["server"]
        room_id = mesh_info["room_id"]
        print(server,room_id)
        logger.info(f"Mesh server: {server}")
    except Exception as e:
        logger.error(f"Failed to get mesh info: {e}")
        return
    
    # Initialize bot
    device_id = "3e8e7a1a3514465ea7d5933cf855d22a"
    bot = RaveBot(
        server=server,
        room_id=room_id,
        peer_id="122414287_3e8e7a1a3514465ea7d5933cf855d22a",
        auth_token=auth_token,
        device_id=device_id,
        command_prefix="!",
        debug=False
    )
    
    # Add event handlers
    @bot.event("on_user_join")
    async def on_user_join_handler(user_info):
        """Handle when a user joins"""
        display_name = user_info.get('displayName') or user_info.get('handle') or f"User {user_info.get('id')}"
        logger.info(f"👋 User joined: {display_name} (ID: {user_info.get('id')})")
        # You can send a message to welcome the user
        # await bot.send_message(f"Welcome {display_name}!")
    
    @bot.event("on_user_left")
    async def on_user_left_handler(user_info):
        """Handle when a user leaves"""
        display_name = user_info.get('displayName') or user_info.get('handle') or f"User {user_info.get('id')}"
        logger.info(f"👋 User left: {display_name} (ID: {user_info.get('id')})")
    
    # Add custom commands
    @bot.command("hello")
    async def hello_command(ctx):
        pprint(vars(ctx))
        """Say hello"""
        await ctx.reply("Hello! 👋")
        
        

            
    @bot.command("search")
    async def search_command(ctx):
        """Search for a video"""
        if ctx.args:
            query = " ".join(ctx.args)
            await ctx.reply(f"Searching for: {query}")
            info = search_and_get_video_data(query)
            await ctx.reply(f"Video found: {info['title']}")
            video_id = get_video_id(info)
            response = vote_video(video_id, room_id, bot.device_id)
            await ctx.reply(f"Video set: {info['title']}")
            
        else:
            await ctx.reply("Usage: !search <query>")
    
    @bot.command("calc")
    async def calc_command(ctx):
        """Simple calculator"""
        if not ctx.args:
            await ctx.reply("Usage: !calc <expression>")
            return
        
        try:
            expression = " ".join(ctx.args)
            # Safe eval for simple math
            result = eval(expression, {"__builtins__": {}}, {})
            await ctx.reply(f"Result: {result}")
        except Exception as e:
            await ctx.reply(f"Error: {str(e)}")
    
    @bot.command("time")
    async def time_command(ctx):
        """Show current time"""
        from datetime import datetime
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        await ctx.reply(f"Current time: {now}")
    
    # Run bot
    logger.info("Starting bot...")
    await bot.run()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Program interrupted by user")
