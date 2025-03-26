import datetime
import logging

from typing import Dict, List
import asyncpg
from pypika import Table, Query, functions as fn


class MethodsSchedule:
    def __init__(self, config: Dict):
        self.db_config = config
        self.users = Table("users_info")
        self.services_info = Table("services_info")
        self.schedule = Table("schedule")
        self.workers = Table("workers_info")
        self.working_time = Table("working_time")

    async def find_free_slots(self, date: datetime.datetime) -> List:
        """Генерирует список свободных слотов в определенный день"""
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
                # создает диапазон промежутков свободных слотов
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
            if not res:
                res = "У вас нет запланированных записей"
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
                .where(
                    self.working_time.time_start <= str(info["date"].time())
                )
                .where(self.working_time.time_end > str(info["date"].time()))
                .where(self.working_time.day_week == info["date"].weekday())
            )
            res = await connection.fetch(str(check_is_working))
            if not res:
                return "Работник в данное время не работает"

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
        """Удаляет запись клиента (Функция администратора)"""
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

    async def delete_schedule_client(self, id: int, date) -> str:
        """Удаляет запись клиента (Функция клиента)"""
        connection = await asyncpg.connect(**self.db_config)
        try:
            find_query = (
                Query.from_(self.schedule)
                .select(self.schedule.id)
                .where(
                    (self.schedule.client_id == id)
                    & (self.schedule.date == date)
                )
            )
            record = await connection.fetchrow(str(find_query))
            if not record:
                return f"У вас нет записи на данное время"

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
        """Сбор статистики записей в диапазоне"""
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
        """Ищем записи, подходящие под уведомление пользователя(за 2 часа += 7.5 минут)"""
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
