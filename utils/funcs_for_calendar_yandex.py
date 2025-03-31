from typing import Dict

import logging
import aiohttp
import asyncio
import ssl
from datetime import datetime, timedelta
from ics import Calendar, Event
from config import USERNAME, PASSWORD, calendar_url


async def add_event(info: Dict):
    # Создаем .ics событие
    if not "client_name" in info.keys():
        client_id = info["client_id"]
        from database.methods import db
        client_name = await db.find_user_name(client_id)
    else:
        client_name = info["client_name"]
    event = Event()
    event.name = info["service_name"]
    event.begin = info["date"] - timedelta(hours=4)
    event.duration = timedelta(hours=1)
    event.uid = info["uid"]
    event.description = (f"Сотрудник: {info["worker_name"]}\n"
                         f"Клиент: {client_name}")

    calendar = Calendar()
    calendar.events.add(event)
    ics_data = calendar.serialize()

    async with aiohttp.ClientSession(auth=aiohttp.BasicAuth(USERNAME, PASSWORD)) as session:
        event_url = f"{calendar_url}{event.uid}.ics"
        headers = {
            "Content-Type": "text/calendar; charset=utf-8"
        }
        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE
        async with session.put(event_url, data=ics_data, headers=headers, ssl=ssl_context) as resp:
            logging.info(f"Статус ответа: {resp.status}")
            if not resp.status in (200, 201, 204):
                text = await resp.text()
                logging.error(f"Ошибка: {text}")


async def delete_event(uid: str):
    event_url = f"{calendar_url}{uid}.ics"
    headers = {
        "Content-Type": "text/calendar; charset=utf-8"
    }
    ssl_context = ssl.create_default_context()
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE

    async with aiohttp.ClientSession(auth=aiohttp.BasicAuth(USERNAME, PASSWORD)) as session:
        async with session.delete(event_url, headers=headers, ssl=ssl_context) as resp:
            print(f"Статус ответа на DELETE: {resp.status}")
            if resp.status in (200, 204):
                print("Событие удалено успешно!")
            elif resp.status == 404:
                print("Событие не найдено.")
            else:
                text = await resp.text()
                print(f"Ошибка: {text}")

