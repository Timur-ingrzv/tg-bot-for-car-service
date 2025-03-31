import datetime
import logging

from typing import Dict
import asyncpg
from pypika import Table, Query


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

        except Exception as e:
            logging.error(e)
            return None

        finally:
            await connection.close()

    async def add_worker(self, worker_name: str) -> str:
        """Добавляет нового сотрудника"""
        connection = await asyncpg.connect(**self.db_config)
        try:
            query = (
                Query.into(self.workers)
                .columns(self.workers.name)
                .insert(worker_name)
            )
            await connection.execute(str(query))
            return f"Работник {worker_name} добавлен"
        except Exception as e:
            logging.error(e)
            return "Ошибка обращения к базе, повторите позже"

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
