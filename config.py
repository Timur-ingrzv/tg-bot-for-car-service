import logging
from dotenv import load_dotenv
import os

# Включаем логирование, чтобы не пропустить важные сообщения
logging.basicConfig(level=logging.INFO)

load_dotenv()
BOT_TOKEN = str(os.getenv("BOT_TOKEN"))
PASSWORD_DB = str(os.getenv("PASSWORD_DB"))
CAR_SERVICE_NAME = "ТЕСТ"

DATABASE_CONFIG = {
    "database": "tg_bot_services",
    "user": "postgres",
    "password": PASSWORD_DB,
    "host": "localhost",
    "port": "5432",
}
