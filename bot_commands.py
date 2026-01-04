"""
Bot command handlers
"""

import asyncio
import logging
import os
import subprocess
import sys
import requests
from pathlib import Path
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
    
    @manager.command("truth")
    async def truth_command(ctx):
        """Get a truth question (rating: PG, PG13, or R)"""
        rating = "PG"  # Default rating
        if ctx.args:
            rating_arg = ctx.args[0].upper()
            if rating_arg in ["PG", "PG13", "R"]:
                rating = rating_arg
            else:
                await ctx.reply(f"❌ Invalid rating. Use PG, PG13, or R. Using default: PG")
        
        try:
            url = f"https://api.truthordarebot.xyz/v1/truth?rating={rating}"
            response = requests.get(url, timeout=5)
            response.raise_for_status()
            data = response.json()
            
            question = data.get("question", "No question available")
            await ctx.reply(f"**Truth ({rating}):**\n{question}")
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching truth question: {e}", exc_info=True)
            await ctx.reply("❌ Failed to fetch truth question. Please try again later.")
        except Exception as e:
            logger.error(f"Error in truth command: {e}", exc_info=True)
            await ctx.reply("❌ An error occurred. Please try again later.")
    
    @manager.command("dare")
    async def dare_command(ctx):
        """Get a dare challenge (rating: PG, PG13, or R)"""
        rating = "PG"  # Default rating
        if ctx.args:
            rating_arg = ctx.args[0].upper()
            if rating_arg in ["PG", "PG13", "R"]:
                rating = rating_arg
            else:
                await ctx.reply(f"❌ Invalid rating. Use PG, PG13, or R. Using default: PG")
        
        try:
            url = f"https://api.truthordarebot.xyz/v1/dare?rating={rating}"
            response = requests.get(url, timeout=5)
            response.raise_for_status()
            data = response.json()
            
            question = data.get("question", "No dare available")
            await ctx.reply(f"**Dare ({rating}):**\n{question}")
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching dare: {e}", exc_info=True)
            await ctx.reply("❌ Failed to fetch dare. Please try again later.")
        except Exception as e:
            logger.error(f"Error in dare command: {e}", exc_info=True)
            await ctx.reply("❌ An error occurred. Please try again later.")
    
    @manager.command("restart")
    async def restart_command(ctx):
        """Restart the bot (Linux only)"""
        # Check if running on Linux
        if sys.platform != "linux":
            await ctx.reply("❌ Restart command is only available on Linux systems.")
            return
        
        # Get the script directory
        script_dir = Path(__file__).parent.absolute()
        restart_script = script_dir / "restart.sh"
        
        # Check if restart script exists
        if not restart_script.exists():
            await ctx.reply("❌ Restart script not found. Please create restart.sh in the bot directory.")
            return
        
        # Make sure script is executable
        try:
            os.chmod(restart_script, 0o755)
        except Exception as e:
            logger.warning(f"Could not set execute permissions on restart.sh: {e}")
        
        await ctx.reply("🔄 Restarting bot... This may take a few seconds.")
        
        try:
            # Execute the restart script in the background
            # Use nohup and redirect output to avoid blocking
            subprocess.Popen(
                ["/bin/bash", str(restart_script)],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True
            )
            # Give it a moment to start
            await asyncio.sleep(1)
            await ctx.reply("✅ Restart command executed. The bot should restart shortly.")
        except Exception as e:
            logger.error(f"Error executing restart script: {e}", exc_info=True)
            await ctx.reply(f"❌ Failed to restart bot: {str(e)}")

