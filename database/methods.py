import asyncio
import datetime
import logging

from typing import Dict, List
import asyncpg
from pypika import Table, Query

from config import DATABASE_CONFIG


class MethodsUsers:
    def __init__(self, config: Dict):
        self.db_config = config
        self.users = Table("users_info")
        self.services_info = Table("services_info")
        self.schedule = Table("schedule")
        self.workers = Table("workers_info")
        self.working_time = Table("working_time")

    async def find_user(self, login: str, password: str) -> Dict:
        """Метод нахождения пользователя по паре логин-пароль"""
        connection = await asyncpg.connect(**self.db_config)
        try:
            query = (
                Query.from_(self.users)
                .select(self.users.id, self.users.name, self.users.status)
                .where(
                    (self.users.login == login)
                    & (self.users.password == password)
                )
            )
            res = await connection.fetchrow(str(query))
            return res

        except Exception as e:
            logging.error(e)
            return {"status": "Ошибка подключения, повторите позже"}

        finally:
            await connection.close()

    async def add_user(self, info: Dict) -> str:
        """Метод добавления нового пользователя"""
        connection = await asyncpg.connect(**self.db_config)
        try:
            user = await self.find_user(info["login"], info["password"])
            if user and user["name"]:
                return "Такой пользователь уже существует"

            query = (
                Query.into(self.users)
                .columns(
                    self.users.name,
                    self.users.login,
                    self.users.password,
                    self.users.phone_number,
                    self.users.chat_id,
                    self.users.status,
                )
                .insert(
                    info["name"],
                    info["login"],
                    info["password"],
                    info["phone_number"],
                    info["chat_id"],
                    info["status"],
                )
            )
            await connection.execute(str(query))
            return "Вы успешно зарегистрировались"

        except Exception as e:
            logging.error(e)
            return "Ошибка подключения, повторите позже"

        finally:
            await connection.close()

    async def change_profile(self, user_id, changed_field, new_value) -> str:
        """Метод изменения данных пользователя"""
        connection = await asyncpg.connect(**self.db_config)
        try:
            field = None
            if changed_field == "name":
                field = self.users.name
            if changed_field == "login":
                field = self.users.login
            if changed_field == "password":
                field = self.users.password
            if changed_field == "phone_number":
                field = self.users.phone_number

            query = (
                Query.update(self.users)
                .set(field, new_value)
                .where(self.users.id == user_id)
            )
            await connection.execute(str(query))
            return "Данные успешно обновлены"

        except Exception as e:
            logging.error(e)
            return "Ошибка подключения, повторите позже"


class MethodsSchedule:
    def __init__(self, config: Dict):
        self.db_config = config
        self.users = Table("users_info")
        self.services_info = Table("services_info")
        self.schedule = Table("schedule")
        self.workers = Table("workers_info")
        self.working_time = Table("working_time")

    async def find_free_slots(self, date: datetime.datetime) -> List:
        connection = await asyncpg.connect(**self.db_config)
        try:
            # ищем всех работников, работающих в этот день
            day_week = date.weekday()
            find_worker_query = (
                Query.from_(self.working_time)
                .select(
                    self.working_time.worker_id,
                    self.working_time.time_start,
                    self.working_time.time_end,
                    self.working_time.day_week,
                )
                .where(self.working_time.day_week == day_week)
            )
            workers = await connection.fetch(str(find_worker_query))

            free_slots = set()
            for worker in workers:
                # создает диапозон промежутков свободных слотов
                start_time = datetime.datetime.combine(
                    date, worker["time_start"]
                )
                end_time = datetime.datetime.combine(date, worker["time_end"])
                end_time -= datetime.timedelta(hours=1)
                query = f"""
                WITH RECURSIVE possible_slots AS (
                    -- Генерируем все возможные слоты
                    SELECT
                        generate_series(
                        '{start_time}'::timestamp,
                        '{end_time}'::timestamp,
                        '1 hour'::interval
                    ) AS slot_time
                ),
                occupied_slots AS (
                    -- Берем занятые слоты работника из таблицы services
                    SELECT date AS slot_time
                    FROM schedule
                    WHERE worker_id = {worker["worker_id"]}  -- ID нужного работника
                )
                -- Находим свободные слоты, исключая занятые
                SELECT slot_time FROM possible_slots
                WHERE slot_time NOT IN (SELECT slot_time FROM occupied_slots);
                """
                res = await connection.fetch(query)
                free_slots.update(res)

            # вытаскиваем время из datetime и сортируем
            free_slots = [
                f"{slot['slot_time'].time().hour:02}:{slot['slot_time'].time().minute:02}"
                for slot in free_slots
            ]
            free_slots.sort()
            return free_slots

        except Exception as e:
            logging.error(e)
            return ["Ошибка обращения к базе, повторите позже"]

        finally:
            await connection.close()

    async def add_schedule(self, data) -> str:
        """Проверяет наличие свободных работников и добавляет запись если есть работник"""
        connection = await asyncpg.connect(**self.db_config)
        try:
            # находим свободных работников в эту дату
            date = data["date"]
            working_workers = (
                Query.from_(self.working_time)
                .select(self.working_time.worker_id)
                .where(
                    (self.working_time.day_week == date.weekday())
                    & (self.working_time.time_start <= str(date.time()))
                    & (self.working_time.time_end > str(date.time()))
                )
            )
            busy_workers = (
                Query.from_(self.schedule)
                .select(self.schedule.worker_id)
                .where(date == self.schedule.date)
            )
            free_workers = (
                Query.from_(self.workers)
                .select(self.workers.id, self.workers.name)
                .where(
                    self.workers.id.isin(working_workers)
                    & self.workers.id.notin(busy_workers)
                )
            )
            workers = await connection.fetch(str(free_workers))
            if not workers:
                return "В данное время нет свободных работников"

            # добавляем новую запись
            service_id = (
                Query.from_(self.services_info)
                .select(self.services_info.id)
                .where(self.services_info.service_name == data["service_name"])
            )
            add_query = (
                Query.into(self.schedule)
                .columns(
                    self.schedule.service_id,
                    self.schedule.client_id,
                    self.schedule.worker_id,
                    self.schedule.date,
                )
                .insert(
                    service_id,
                    data["client_id"],
                    workers[0]["id"],
                    data["date"],
                )
            )
            await connection.execute(str(add_query))
            return f"Вы успешно записались на {data['date'].strftime('%d-%m-%Y %H-%M')}"

        except Exception as e:
            logging.error(e)
            return "Ошибка обращения к базе, повторите позже"

        finally:
            await connection.close()

    async def show_schedule(self, user_id):
        """Выводит все запланированные записи пользователя"""
        connection = await asyncpg.connect(**self.db_config)
        try:
            cur_date = datetime.datetime.now()
            query = (
                Query.from_(self.schedule)
                .join(self.workers)
                .on(self.schedule.worker_id == self.workers.id)
                .join(self.services_info)
                .on(self.schedule.service_id == self.services_info.id)
                .select(
                    self.services_info.service_name,
                    self.services_info.price,
                    self.workers.name,
                    self.schedule.date,
                )
                .where(self.schedule.client_id == user_id)
                .where(cur_date < self.schedule.date)
            )
            res = await connection.fetch(str(query))
            return res

        except Exception as e:
            logging.error(e)
            return "Ошибка обращения к базе, повторите позже"

        finally:
            await connection.close()

    async def delete_schedule(self, name, date) -> str:
        connection = await asyncpg.connect(**self.db_config)
        try:
            find_query = (
                Query.from_(self.schedule)
                .join(self.users)
                .on(self.users.id == self.schedule.client_id)
                .join(self.workers)
                .on(self.workers.id == self.schedule.worker_id)
                .select(self.schedule.id)
                .where(self.schedule.date == date)
                .where((self.workers.name == name) | (self.users.name == name))
            )
            record = await connection.fetchrow(str(find_query))
            if not record:
                return f"Записи в данное время для {name} не существует"

            query = (
                Query.from_(self.schedule)
                .delete()
                .where(self.schedule.id == record["id"])
            )
            await connection.execute(str(query))
            return "Запись успешно удалена"

        except Exception as e:
            logging.error(e)
            return "Ошибка обращения к базе, повторите позже"

        finally:
            await connection.close()


class MethodsServices:
    def __init__(self, config: Dict):
        self.db_config = config
        self.users = Table("users_info")
        self.services_info = Table("services_info")
        self.schedule = Table("schedule")
        self.workers = Table("workers_info")
        self.working_time = Table("working_time")

    async def show_services(self):
        connection = await asyncpg.connect(**self.db_config)
        try:
            query = Query.from_(self.services_info).select(
                self.services_info.service_name, self.services_info.price
            )
            res = await connection.fetch(str(query))
            return res

        except Exception as e:
            logging.error(e)
            return "Ошибка обращения к базе, повторите позже"

        finally:
            await connection.close()


class Database(MethodsUsers, MethodsSchedule, MethodsServices):
    def __init__(self, conf):
        super().__init__(conf)


db = Database(DATABASE_CONFIG)
info = {
    "name": "test_name",
    "login": "test_login",
    "password": "test_password",
    "status": "client",
    "phone_number": "9894",
    "chat_id": "123",
}
date = datetime.datetime.strptime("22-12-2024 17", "%d-%m-%Y %H")
res = asyncio.run(db.delete_schedule("test_worker", date))
print(res)
