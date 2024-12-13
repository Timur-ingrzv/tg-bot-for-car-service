import asyncio
import logging
from typing import Dict

import asyncpg
from pypika import Table, Query, Order, functions as fn

from config import DATABASE_CONFIG


class MethodsUnauthorized:
    def __init__(self, config: Dict):
        self.db_config = config
        self.users = Table("users_info")

    async def find_user(self, login: str, password: str) -> Dict:
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
        connection = await asyncpg.connect(**self.db_config)
        try:
            field = None
            match changed_field:
                case "name":
                    field = self.users.name
                case "login":
                    field = self.users.login
                case "password":
                    field = self.users.password
                case "phone_number":
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


class Database(MethodsUnauthorized):
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
# print(asyncio.run(db.change_profile(1, "name", "test_client1")))
