"""
Bot event handlers
"""

import logging
from rave_api.utils import ai_utils
from pprint import pprint
logger = logging.getLogger(__name__)

# Configuration for AI responses
AUTO_RESPOND = True  # Set to False to disable automatic AI responses


def register_events(manager):
    """Register all bot event handlers with the manager"""
    
    @manager.event("on_user_join")
    async def on_user_join_handler(bot, user_info):
        """Handle when a user joins any mesh"""
        # pprint(user_info)
        # Handle both displayName and name fields
        user_name = user_info.get('displayName') or user_info.get('name') or user_info.get('handle') or 'User'
        await bot.send_message(f"welcome {user_name} to the chat")
    
    @manager.event("on_user_left")
    async def on_user_left_handler(user_info):
        """Handle when a user leaves any mesh"""
        pass  # Removed logging as per cleanup requirements
    
    @manager.event("on_connected")
    async def on_connected_handler(bot):
        """Handle when bot connects to a mesh - send hello message"""
        if not hasattr(bot, 'video_info_map'):
            bot.video_info_map = {}
        # await bot.send_message("hello everyone")
    
    @manager.event("on_message")
    async def on_message_handler(message_info):
        """Handle chat messages and generate AI responses"""
        if not AUTO_RESPOND:
            return
        
        message_text = message_info.get("message", "")
        user_name = message_info.get("sender_name", "Unknown User")
        mesh_id = message_info.get("mesh_id", "")
        message_id = message_info.get("message_id", "")
        bot = message_info.get("bot")
        
        is_reply_to_bot = message_info.get("is_reply_to_bot", False)
        is_mentioned = message_info.get("is_mentioned", False)
        
        should_respond = is_mentioned or is_reply_to_bot
        if not should_respond:
            return
        
        if not message_text or not message_text.strip():
            return
        
        ai_utils.add_user_message(mesh_id, user_name, message_text)
        ai_response = ai_utils.get_response(mesh_id)
        
        if ai_response and bot:
            await bot.send_message(ai_response, reply_to=message_id if message_id else None)

