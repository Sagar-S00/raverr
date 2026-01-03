"""
Bot command handlers
"""

import logging
from rave_api.utils import get_video_id, vote_video
from video_utils import search_and_send_videos, find_video_info_by_reply

logger = logging.getLogger(__name__)


def register_commands(manager):
    """Register all bot commands with the manager"""
    
    @manager.command("hello")
    async def hello_command(ctx):
        """Say hello"""
        await ctx.reply("Hello! 👋 I'm a multi-mesh bot!")
    
    @manager.command("status")
    async def status_command(ctx):
        """Show bot manager status"""
        status = manager.get_status()
        status_text = f"**Bot Manager Status:**\n"
        status_text += f"Running: {status['is_running']}\n"
        status_text += f"Total Bots: {status['total_bots']}\n"
        status_text += f"Connected: {sum(1 for b in status['bots'].values() if b['state'] == 'connected')}"
        await ctx.reply(status_text)
    
    @manager.command("meshinfo")
    async def meshinfo_command(ctx):
        """Show current mesh information"""
        mesh_id = ctx.bot.room_id
        info = f"**Mesh Info:**\n"
        info += f"Mesh ID: `{mesh_id[:8]}...`\n"
        info += f"Server: `{ctx.bot.server}`"
        await ctx.reply(info)
    
    @manager.command("set")
    async def set_command(ctx):
        """Set/vote for a video by replying to a search result"""
        message_data = ctx.message_data.get("data", {})
        reply_to = message_data.get("reply")
        
        if not reply_to:
            await ctx.reply("❌ Please reply to a search result to set a video. Use `?search <query>` first.")
            return
        
        bot = ctx.bot
        if not hasattr(bot, 'video_info_map'):
            bot.video_info_map = {}
        
        video_info = find_video_info_by_reply(bot, reply_to)
        
        if video_info:
            room_id = bot.room_id
            video_id = get_video_id(video_info)
            vote_video(video_id, room_id, bot.device_id)
            await ctx.reply(f"✅ Video set: {video_info['title']}")
        else:
            await ctx.reply("❌ No video found for this message. Make sure you're replying to a search result.")
    
    @manager.command("search")
    async def search_command(ctx):
        """Search for videos and show top 3 results with thumbnails"""
        if ctx.args:
            query = " ".join(ctx.args)
            await ctx.reply(f"Searching for: {query}")
            await search_and_send_videos(ctx.bot, query)
        else:
            prefixes = ", ".join(ctx.bot.command_prefixes)
            await ctx.reply(f"Usage: {prefixes[0]}search <query>")

