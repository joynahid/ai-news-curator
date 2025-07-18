from io import BytesIO
from telegram.ext import ApplicationBuilder


class TelegramSender:
    def __init__(self, bot_token: str, chat_id: str = None):
        """
        Initialize Telegram sender with bot token and optional chat ID

        Args:
            bot_token (str): Your Telegram bot token
            chat_id (str): Target chat ID (can be set later)
        """
        self.bot_token = bot_token
        self.chat_id = chat_id
        self.app = ApplicationBuilder().token(bot_token).build()

    async def send_message(self, text: str, chat_id: str = None) -> bool:
        """
        Send a text message to a Telegram chat

        Args:
            text (str): Message text to send
            chat_id (str): Target chat ID (uses self.chat_id if not provided)

        Returns:
            bool: True if message sent successfully, False otherwise
        """
        try:
            target_chat_id = chat_id or self.chat_id
            if not target_chat_id:
                raise ValueError("No chat_id provided")

            await self.app.bot.send_message(
                chat_id=target_chat_id, text=text, parse_mode="Markdown"
            )
            print(f"✅ Message sent successfully to chat {target_chat_id}")
            return True

        except Exception as e:
            print(f"❌ Failed to send message: {e}")
            return False

    async def send_photo_with_message(
        self, photo_path: BytesIO, text: str, chat_id: str = None
    ) -> bool:
        """
        Send a photo with a separate text message

        Args:
            photo_path (BytesIO): Path to the photo file
            text (str): Text message to send
            chat_id (str): Target chat ID (uses self.chat_id if not provided)

        Returns:
            bool: True if both photo and message sent successfully, False otherwise
        """
        try:
            target_chat_id = chat_id or self.chat_id
            if not target_chat_id:
                raise ValueError("No chat_id provided")

            # Send photo first
            photo_success = await self.send_photo(photo_path, chat_id=target_chat_id)
            if not photo_success:
                return False

            # Send text message
            message_success = await self.send_message(text, chat_id=target_chat_id)
            return message_success

        except Exception as e:
            print(f"❌ Failed to send photo with message: {e}")
            return False
