import asyncio
import logging
from database.methods import db

DELAY = 15 * 60


async def notifications():
    logging.info("Запуск итерации уведомлений")
    users = await db.find_service_for_notification(DELAY)
    for note in users:
        logging.info("Найдена запись")
        ans = (
            f"<b>Напоминание о записи</b>\n"
            f"<b>Название услуги:</b> {note['service_name']}\n"
            f"<b>Цена:</b> {note['price']}\n"
            f"<b>Работник:</b> {note['name']}\n"
            f"<b>Дата:</b> {note['date'].strftime('%d-%m-%Y %H:%M')}\n"
        )
        try:
            from bot import bot

            await bot.send_message(note["chat_id"], ans, parse_mode="HTML")
        except Exception as e:
            logging.error(e)
            continue

