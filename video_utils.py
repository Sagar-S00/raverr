"""
Video search and upload utilities
"""

import tempfile
import os
import requests
import logging
from youtube_search import search_and_get_video_data
from rave_api.utils import upload_media

logger = logging.getLogger(__name__)


async def search_and_send_videos(bot, query: str):
    """Search for videos and send top 3 results with thumbnails"""
    try:
        results = search_and_get_video_data(query, limit=3)
        
        if not results:
            await bot.send_message("❌ No videos found")
            return
        
        if not hasattr(bot, 'video_info_map'):
            bot.video_info_map = {}
        
        temp_files = []
        try:
            for video_info in results:
                thumbnail_url = video_info.get('thumbnail')
                if not thumbnail_url:
                    continue
                
                response = requests.get(thumbnail_url, timeout=10)
                response.raise_for_status()
                
                temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.jpg')
                temp_file.write(response.content)
                temp_file.close()
                temp_files.append(temp_file.name)
                
                room_id = bot.room_id
                uploaded_media = upload_media(
                    room_id,
                    [temp_file.name],
                    is_explicit=False
                )
                
                if not uploaded_media:
                    continue
                
                media_item = uploaded_media[0]
                title = video_info['title']
                author = video_info.get('author', 'Unknown')
                message_text = f"{title}\nby {author}"
                
                sent_message_id = await bot.send_message(
                    message_text,
                    media=[media_item]
                )
                
                if sent_message_id:
                    bot.video_info_map[sent_message_id] = video_info
                    
                    if hasattr(bot, 'recent_bot_messages'):
                        for msg in reversed(bot.recent_bot_messages):
                            msg_id = msg.get('id')
                            msg_content = msg.get('content', '')
                            if msg_id == sent_message_id or msg_content == message_text:
                                msg['video_info'] = video_info
                                break
                        else:
                            if bot.recent_bot_messages:
                                bot.recent_bot_messages[-1]['video_info'] = video_info
        
        finally:
            for temp_file in temp_files:
                try:
                    if os.path.exists(temp_file):
                        os.unlink(temp_file)
                except Exception:
                    pass
    
    except Exception as e:
        logger.error(f"Error searching for video: {e}", exc_info=True)
        await bot.send_message(f"❌ Error searching for video: {str(e)}")


def find_video_info_by_reply(bot, reply_to: str):
    """Find video info by reply message ID"""
    video_info = bot.video_info_map.get(reply_to)
    if video_info:
        return video_info
    
    if not hasattr(bot, 'bot_message_ids') or reply_to not in bot.bot_message_ids:
        return None
    
    if hasattr(bot, 'recent_bot_messages'):
        for msg in bot.recent_bot_messages:
            msg_id = msg.get('id')
            if msg_id == reply_to or (reply_to in bot.bot_message_ids and msg_id in bot.bot_message_ids):
                if 'video_info' in msg:
                    video_info = msg['video_info']
                    bot.video_info_map[reply_to] = video_info
                    return video_info
        
        for msg in reversed(bot.recent_bot_messages):
            if 'video_info' in msg and msg.get('id') in bot.bot_message_ids:
                video_info = msg['video_info']
                bot.video_info_map[reply_to] = video_info
                return video_info
    
    return None

