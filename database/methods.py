import asyncio
import logging
from typing import Dict, final

import asyncpg
from pypika import Table, Query, Order, functions as fn

from config import DATABASE_CONFIG


class Database:
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


db = Database(DATABASE_CONFIG)
