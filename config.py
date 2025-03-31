import logging
from dotenv import load_dotenv
from cryptography.fernet import Fernet
import os

# Включаем логирование, чтобы не пропустить важные сообщения
logging.basicConfig(level=logging.INFO)

load_dotenv()
BOT_TOKEN = str(os.getenv("BOT_TOKEN"))
PASSWORD_DB = str(os.getenv("PASSWORD_DB"))
KEY_HASH = str(os.getenv("KEY_HASH"))
CAR_SERVICE_NAME = "ТЕСТ"

hasher = Fernet(KEY_HASH)
DATABASE_CONFIG = {
    "database": "tg_bot_services",
    "user": "postgres",
    "password": PASSWORD_DB,
    "host": "localhost",
    "port": "5432",
}

YANDEX_CALDAV_URL = "https://caldav.yandex.ru"
USERNAME = "Timuraka47@yandex.ru"
PASSWORD = str(os.getenv("PASSWORD_DB"))
calendar_url = f"https://caldav.yandex.ru/calendars/{USERNAME}/events-32174114/"
