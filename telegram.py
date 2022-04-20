import requests

from medium import Medium
from constants import TELEGRAM_TEST_TTBOT_TOKEN, TELEGRAM_CHAT_ID, TELEGRAM_API_URL
from setup_logger import logger, log
from story import Story

# https://api.telegram.org/bot[BOT_API_KEY]/[methodName]


class Telegram(Medium):
    def __init__(self, bot_token=TELEGRAM_TEST_TTBOT_TOKEN, chat_id=TELEGRAM_CHAT_ID):
        super().__init__()
        self.bot_token = bot_token
        self.chat_id = chat_id

    def notify(self, story: Story):
        self.publish_to_telegram(story.formatted_title, story.formatted_body)

    def publish_to_telegram(self, title: str, story: str):
        log(f"Publishing to telegram: {title}")
        try:
            self.send_to_telegram_channel(f"<b><u>{title}</u></b>\n\n{story}")
        except requests.exceptions.SSLError as e:
            logger.error(f"Error while publishing to Telegram: {e}")

    def send_to_telegram_channel(self, message: str):
        response = requests.get(TELEGRAM_API_URL + "sendMessage", params={
            "chat_id": self.chat_id,
            "text": message,
            "parse_mode": "HTML",
        })
        response.raise_for_status()
