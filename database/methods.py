import asyncio
import datetime
import logging

from typing import Dict, List
import asyncpg
from pypika import Table, Query, functions as fn

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

    async def change_chat_id(self, user_id, chat_id) -> None:
        connection = await asyncpg.connect(**self.db_config)
        try:
            query = (
                Query.update(self.users)
                .set(self.users.chat_id, chat_id)
                .where(self.users.id == user_id)
            )
            await connection.execute(str(query))

        except Exception as e:
            logging.error(e)

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

    async def show_schedule_admin(self, start, end):
        """Показывает все записи за промежуток"""
        connection = await asyncpg.connect(**self.db_config)
        try:
            query = (
                Query.from_(self.schedule)
                .join(self.workers)
                .on(self.workers.id == self.schedule.worker_id)
                .join(self.users)
                .on(self.users.id == self.schedule.client_id)
                .join(self.services_info)
                .on(self.services_info.id == self.schedule.service_id)
                .select(
                    self.users.name.as_("client_name"),
                    self.workers.name.as_("worker_name"),
                    self.schedule.date,
                    self.services_info.service_name,
                    self.services_info.price,
                )
                .where(self.schedule.date[start:end])
            )
            res = await connection.fetch(str(query))
            return res

        except Exception as e:
            logging.error(e)
            return "Ошибка обращения к базе, повторите позже"

        finally:
            await connection.close()

    async def add_schedule_admin(self, info: Dict):
        """Добавляет запись для клиента"""
        connection = await asyncpg.connect(**self.db_config)
        try:
            find_client = (
                Query.from_(self.users)
                .select(self.users.id)
                .where(self.users.name == info["client_name"])
            )
            res = await connection.fetchrow(str(find_client))
            if not res:
                return "Клиента с таким именем не существует"
            client_id = res["id"]

            find_worker = (
                Query.from_(self.workers)
                .select(self.workers.id)
                .where(self.workers.name == info["worker_name"])
            )
            res = await connection.fetchrow(str(find_worker))
            if not res:
                return "Работника с таким именем не существует"
            worker_id = res["id"]

            find_service = (
                Query.from_(self.services_info)
                .select(self.services_info.id)
                .where(self.services_info.service_name == info["service_name"])
            )
            res = await connection.fetchrow(str(find_service))
            if not res:
                return "Услуги с таким названием не существует"
            service_id = res["id"]

            check_worker_time = (
                Query.from_(self.schedule)
                .select(self.schedule.id)
                .where(self.schedule.date == info["date"])
                .where(self.schedule.worker_id == worker_id)
            )
            res = await connection.fetch(str(check_worker_time))
            if res:
                return "Работник в данное время занят"
            check_is_working = (
                Query.from_(self.working_time)
                .select(self.working_time.id)
                .where(self.working_time.start <= str(info["date"].time()))
                .where(self.working_time.end < str(info["date"].time()))
                .where(self.working_time.day_week == info["date"].da)
            )
            query = (
                Query.into(self.schedule)
                .columns(
                    self.schedule.service_id,
                    self.schedule.client_id,
                    self.schedule.worker_id,
                    self.schedule.date,
                )
                .insert(service_id, client_id, worker_id, info["date"])
            )
            await connection.execute(str(query))
            return "Запись успешно добавлена"

        except Exception as e:
            logging.error(e)
            return "Ошибка обращения к базе, повторите позже"

        finally:
            await connection.close()

    async def delete_schedule(self, name, date) -> str:
        """Удаляет запись клиента"""
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

    async def get_statistic(self, start_date, end_date):
        connection = await asyncpg.connect(**self.db_config)
        try:
            query_payouts = (
                Query.from_(self.schedule)
                .join(self.workers)
                .on(self.workers.id == self.schedule.worker_id)
                .join(self.services_info)
                .on(self.services_info.id == self.schedule.service_id)
                .select(
                    self.workers.name,
                    fn.Sum(self.services_info.price).as_("total_price"),
                    fn.Count(self.schedule.id).as_("total_services"),
                    fn.Sum(self.services_info.payout_worker).as_("payout"),
                )
                .where(self.schedule.date[start_date:end_date])
                .groupby(self.workers.name)
                .orderby(self.workers.name)
            )
            res = await connection.fetch(str(query_payouts))
            return res

        except Exception as e:
            logging.error(e)
            return "Ошибка обращения к базе, повторите позже"

        finally:
            await connection.close()

    async def find_service_for_notification(self, delay):
        connection = await asyncpg.connect(**self.db_config)
        try:
            cur_time = datetime.datetime.now() + datetime.timedelta(hours=2)
            delta = datetime.timedelta(seconds=delay / 2 + 5)
            query = (
                Query.from_(self.schedule)
                .join(self.users)
                .on(self.users.id == self.schedule.client_id)
                .join(self.services_info)
                .on(self.services_info.id == self.schedule.service_id)
                .join(self.workers)
                .on(self.workers.id == self.schedule.worker_id)
                .select(
                    self.users.chat_id,
                    self.services_info.service_name,
                    self.services_info.price,
                    self.workers.name,
                    self.schedule.date,
                )
                .where(self.schedule.date[cur_time - delta : cur_time + delta])
            )
            res = await connection.fetch(str(query))
            return res

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
        """Показывает доступные услуги"""
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


class MethodsWorkers:
    def __init__(self, config: Dict):
        self.db_config = config
        self.users = Table("users_info")
        self.services_info = Table("services_info")
        self.schedule = Table("schedule")
        self.workers = Table("workers_info")
        self.working_time = Table("working_time")

    async def find_worker(self, name: str) -> int:
        """Находит id рабочего по имени"""
        connection = await asyncpg.connect(**self.db_config)
        try:
            query = (
                Query.from_(self.workers)
                .select(self.workers.id)
                .where(self.workers.name == name)
            )
            worker_id = await connection.fetchrow(str(query))
            if not worker_id:
                return None
            else:
                return worker_id["id"]

        finally:
            await connection.close()

    async def show_working_time(self, worker_name):
        """Показывает время работы работника по дням"""
        connection = await asyncpg.connect(**self.db_config)
        try:
            worker_id = await self.find_worker(worker_name)
            if not worker_id:
                return "Работника с таким именем нет"

            query = (
                Query.from_(self.working_time)
                .select(
                    self.working_time.time_start,
                    self.working_time.time_end,
                    self.working_time.day_week,
                )
                .where(worker_id == self.working_time.worker_id)
                .orderby(self.working_time.day_week)
            )
            res = await connection.fetch(str(query))
            return res

        except Exception as e:
            logging.error(e)
            return "Ошибка обращения к базе, повторите позже"

        finally:
            await connection.close()

    async def add_working_time(
        self,
        worker_id: int,
        start: datetime.datetime,
        end: datetime.datetime,
        weekday: int,
    ) -> str:
        """Добавляет время работы сотрудника"""
        connection = await asyncpg.connect(**self.db_config)
        try:
            check_query = (
                Query.from_(self.working_time)
                .select(self.working_time.id)
                .where(self.working_time.worker_id == worker_id)
                .where(self.working_time.day_week == weekday)
            )
            check = await connection.fetch(str(check_query))
            if check:
                res = await self.change_working_time(
                    worker_id, start, end, weekday
                )
                return res

            query = (
                Query.into(self.working_time)
                .columns(
                    self.working_time.worker_id,
                    self.working_time.time_start,
                    self.working_time.time_end,
                    self.working_time.day_week,
                )
                .insert(
                    worker_id,
                    start.strftime("%H:00"),
                    end.strftime("%H:00"),
                    weekday,
                )
            )
            await connection.execute(str(query))
            return "Время работы успешно изменено"

        except Exception as e:
            logging.error(e)
            return "Ошибка обращения к базе, повторите позже"

        finally:
            await connection.close()

    async def change_working_time(
        self,
        worker_id: int,
        start: datetime.datetime,
        end: datetime.datetime,
        weekday: int,
    ) -> str:
        """Меняет время работы сотрудника"""
        connection = await asyncpg.connect(**self.db_config)
        try:
            query = (
                Query.update(self.working_time)
                .set(self.working_time.time_start, start.strftime("%H:00"))
                .set(self.working_time.time_end, end.strftime("%H:00"))
                .where(self.working_time.worker_id == worker_id)
                .where(self.working_time.day_week == weekday)
            )
            await connection.execute(str(query))
            return "Время работы успешно изменено"

        except Exception as e:
            logging.error(e)
            return "Ошибка обращения к базе, повторите позже"

        finally:
            await connection.close()

    async def delete_working_time(self, worker_id: int, weekday: int) -> str:
        """Удаляет время работы в определенный день недели"""
        connection = await asyncpg.connect(**self.db_config)
        try:
            query = (
                Query.from_(self.working_time)
                .delete()
                .where(self.working_time.worker_id == worker_id)
                .where(self.working_time.day_week == weekday)
            )
            await connection.execute(str(query))
            return "Время работы успешно удалено"

        except Exception as e:
            logging.error(e)
            return "Ошибка обращения к базе, повторите позже"

        finally:
            await connection.close()

    async def show_workers_info(self):
        connection = await asyncpg.connect(**self.db_config)
        try:
            date = datetime.datetime.now()
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
                .where(date.strftime("%Y-%m-%d %H:00") == self.schedule.date)
            )
            query_working_free = (
                Query.from_(self.workers)
                .select(self.workers.name)
                .where(
                    self.workers.id.isin(working_workers)
                    & self.workers.id.notin(busy_workers)
                )
            )
            working_free = await connection.fetch(str(query_working_free))

            query_working_not_free = (
                Query.from_(self.workers)
                .select(self.workers.name)
                .where(self.workers.id.isin(working_workers))
                .where(self.workers.name.notin(query_working_free))
            )
            working_not_free = await connection.fetch(
                str(query_working_not_free)
            )

            query_not_working = (
                Query.from_(self.workers)
                .select(self.workers.name)
                .where(self.workers.id.notin(working_workers))
            )
            not_working = await connection.fetch(str(query_not_working))
            return {
                "working_free": working_free,
                "working_not_free": working_not_free,
                "not_working": not_working,
            }

        except Exception as e:
            logging.error(e)
            return "Ошибка обращения к базе, повторите позже"

        finally:
            await connection.close()


class Database(MethodsUsers, MethodsSchedule, MethodsServices, MethodsWorkers):
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
date1 = datetime.datetime.strptime("22-01-2025 17", "%d-%m-%Y %H")
date2 = datetime.datetime.strptime("01-02-2025", "%d-%m-%Y")

info = {
    "date": datetime.datetime.now(),
    "client_name": "test_client1",
    "worker_name": "test_worker",
    "service_name": "Диагностика",
}
start = datetime.datetime.strptime("2025-02-04 18:52", "%Y-%m-%d %H:%M")

end = datetime.datetime.strptime("2026-04-05", "%Y-%m-%d")

res = asyncio.run(db.find_service_for_notification(60))
print(res)
