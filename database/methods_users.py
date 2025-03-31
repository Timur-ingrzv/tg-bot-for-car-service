import logging

from typing import Dict
import asyncpg
from pypika import Table, Query

from config import hasher


class MethodsUsers:
    def __init__(self, config: Dict):
        self.db_config = config
        self.users = Table("users_info")
        self.services_info = Table("services_info")
        self.schedule = Table("schedule")
        self.workers = Table("workers_info")
        self.working_time = Table("working_time")

    async def check_existing(self, name: str = "", login: str = "") -> bool:
        connection = await asyncpg.connect(**self.db_config)
        try:
            if name != "":
                column = self.users.name
                check = name
            else:
                column = self.users.login
                check = login

            query = (
                Query.from_(self.users)
                .select(self.users.id)
                .where(column == check)
            )
            res = await connection.fetch(str(query))
            return bool(res)

        except Exception as e:
            logging.error(e)
            return "Ошибка подключения, повторите позже"

        finally:
            await connection.close()

    async def find_user(self, login: str, password: str) -> Dict:
        """Метод нахождения пользователя по паре логин-пароль"""
        connection = await asyncpg.connect(**self.db_config)
        try:
            query = (
                Query.from_(self.users)
                .select(
                    self.users.id,
                    self.users.name,
                    self.users.password,
                    self.users.status,
                )
                .where(self.users.login == login)
            )
            users = await connection.fetch(str(query))
            password = password.encode("UTF-8")
            for user in users:
                unhashed_password = hasher.decrypt(user["password"])
                if password == unhashed_password:
                    return user
            return None

        except Exception as e:
            logging.error(e)
            return {"status": "Ошибка подключения, повторите позже"}

        finally:
            await connection.close()

    async def find_all_users(self, page: int):
        connection = await asyncpg.connect(**self.db_config)
        try:
            query = (
                Query.from_(self.users)
                .select(self.users.name)
                .limit(10)
                .offset((page - 1) * 10)
                .orderby(self.users.name)
                .where(self.users.status == "client")
            )
            res = await connection.fetch(str(query))
            return [user["name"] for user in res]

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
            info["password"] = hasher.encrypt(
                info["password"].encode("UTF-8")
            ).decode("UTF-8")
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
                new_value = hasher.encrypt(new_value.encode("UTF-8")).decode(
                    "UTF-8"
                )
            if changed_field == "phone_number":
                field = self.users.phone_number

            check_query = (
                Query.from_(self.users)
                .select(self.users.id)
                .where(field == new_value)
            )
            check = await connection.fetch(str(check_query))
            if check and changed_field in ("name", "login"):
                return "Данное значение уже занято, попробуйте другое"

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

        finally:
            await connection.close()

    async def delete_user(self, name: str, id_admin: int) -> str:
        connection = await asyncpg.connect(**self.db_config)
        try:
            check_exist_query = (
                Query.from_(self.users)
                .select(self.users.id)
                .where(self.users.name == name)
            )
            res = await connection.fetch(str(check_exist_query))
            if not res:
                return "Пользователя с таким именем не существует"

            check_self_query = (
                Query.from_(self.users)
                .select(self.users.id)
                .where(self.users.id == id_admin)
                .where(self.users.name == name)
            )
            res = await connection.fetch(str(check_self_query))
            if res:
                return "Нельзя удалить свой профиль"

            query = (
                Query.from_(self.users).delete().where(self.users.name == name)
            )
            await connection.execute(str(query))
            return "Пользователь удален"

        except Exception as e:
            logging.error(e)
            return "Ошибка подключения, повторите позже"

        finally:
            await connection.close()

    async def show_user_info(self, name: str):
        connection = await asyncpg.connect(**self.db_config)
        try:
            query = (
                Query.from_(self.users)
                .select(
                    self.users.id,
                    self.users.login,
                    self.users.password,
                    self.users.phone_number,
                    self.users.status,
                )
                .where(self.users.name == name)
            )
            res = await connection.fetchrow(str(query))
            res = dict(res)
            if res:
                res["password"] = hasher.decrypt(res["password"]).decode(
                    "UTF-8"
                )
            return res

        except Exception as e:
            logging.error(e)
            return "Ошибка подключения, повторите позже"

        finally:
            await connection.close()
