import logging

from typing import Dict
import asyncpg
from pypika import Table, Query


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
            query = (
                Query.from_(self.services_info)
                .select(
                    self.services_info.service_name,
                    self.services_info.price,
                    self.services_info.payout_worker,
                )
                .orderby(self.services_info.service_name)
            )
            res = await connection.fetch(str(query))
            return res

        except Exception as e:
            logging.error(e)
            return "Ошибка обращения к базе, повторите позже"

        finally:
            await connection.close()

    async def check_service_existing(self, service_name: str) -> int:
        connection = await asyncpg.connect(**self.db_config)
        try:
            query_check = (
                Query.from_(self.services_info)
                .select(self.services_info.id)
                .where(self.services_info.service_name == service_name)
            )
            res = await connection.fetch(str(query_check))
            if res:
                return 1
            else:
                return 0

        except Exception as e:
            logging.error(e)
            return -1

        finally:
            await connection.close()

    async def add_service(
        self, service_name: str, price: int, payout: int
    ) -> str:
        """Добавляет новую услугу"""
        connection = await asyncpg.connect(**self.db_config)
        try:
            # Добавляем услугу
            query = (
                Query.into(self.services_info)
                .columns(
                    self.services_info.service_name,
                    self.services_info.price,
                    self.services_info.payout_worker,
                )
                .insert(service_name, price, payout)
            )
            await connection.execute(str(query))
            return "Услуга добавлена"

        except Exception as e:
            logging.error(e)
            return "Ошибка обращения к базе, повторите позже"

        finally:
            await connection.close()

    async def delete_service(self, service_name: str) -> str:
        """Удаляет услугу"""
        connection = await asyncpg.connect(**self.db_config)
        try:
            query = (
                Query.from_(self.services_info)
                .delete()
                .where(self.services_info.service_name == service_name)
            )
            await connection.execute(str(query))
            return "Услуга удалена"

        except Exception as e:
            logging.error(e)
            return "Ошибка обращения к базе, повторите позже"

        finally:
            await connection.close()

    async def change_service_info(
        self, service_name: str, col: str, new_value: int
    ) -> str:
        """Меняет цену или выплату услуги"""
        connection = await asyncpg.connect(**self.db_config)
        try:
            # проверка корректности цены и выплаты
            query_check = (
                Query.from_(self.services_info)
                .select(
                    self.services_info.price, self.services_info.payout_worker
                )
                .where(self.services_info.service_name == service_name)
            )
            service = await connection.fetchrow(str(query_check))

            if col == "price":
                field = self.services_info.price
                if service["payout_worker"] > new_value:
                    return (
                        "Выплата сотруднику не может быть больше цены услуги"
                    )
            else:
                field = self.services_info.payout_worker
                if service["price"] < new_value:
                    return (
                        "Выплата сотруднику не может быть больше цены услуги"
                    )
            query = (
                Query.update(self.services_info)
                .set(field, new_value)
                .where(self.services_info.service_name == service_name)
            )
            await connection.execute(str(query))
            return "Данные изменены"

        except Exception as e:
            logging.error(e)
            return "Ошибка обращения к базе, повторите позже"

        finally:
            await connection.close()
