"""
Command context for Rave Bot
"""

from typing import Dict, Any


class CommandContext:
    """Context object passed to command handlers"""
    
    def __init__(self, bot, message_data: Dict[str, Any], command: str, args: list):
        self.bot = bot
        self.message_data = message_data
        self.command = command
        self.args = args
        self.sender = message_data.get("data", {}).get("from", "unknown")
        self.message_id = message_data.get("data", {}).get("id", "")
        self.raw_message = message_data.get("data", {}).get("chat", "")
    
    async def reply(self, text: str):
        """Reply to the command (includes reply reference to original message)"""
        await self.bot.send_message(text, reply_to=self.message_id if self.message_id else None)
    
    async def send(self, text: str):
        """Send a message (alias for reply)"""
        await self.reply(text)

