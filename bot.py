import asyncio
import config
from aiogram import Bot, Dispatcher
from aiogram.filters.command import Command, Message

from handlers import handlers_unauthorized_user, handlers_administration_user, handlers_clients_user
from utils.middleware import StatusMiddleware, User_status
from utils.filters import IsAuthorizedFilter, IsUnauthorized, IsAdminFilter, UserStatus
from keyboards import keyboards_unauthorized_user


# Объект бота
bot = Bot(token=config.TOKEN)
# Диспетчер
dp = Dispatcher()

# Запуск процесса поллинга новых апдейтов
async def main():
    dp.update.middleware(StatusMiddleware())
    dp.include_routers(handlers_unauthorized_user.router, handlers_administration_user.router)

    handlers_unauthorized_user.router.message.filter(IsUnauthorized())
    handlers_unauthorized_user.router.callback_query.filter(IsUnauthorized())

    handlers_administration_user.router.message.filter(IsAdminFilter())
    handlers_administration_user.router.callback_query.filter(IsAdminFilter())

    #handlers_clients_user.router.message.filter(IsAuthorizedFilter())
    await dp.start_polling(bot)

@dp.message(Command("start"))
async def cmd_start(message: Message):
    User_status[message.from_user.id] = UserStatus.UNAUTHORIZED_USER
    await message.answer(f"Добро пожаловать в автосервис {config.CAR_SERVICE_NAME}\n",
                         reply_markup=keyboards_unauthorized_user.get_start_keyboard())

if __name__ == "__main__":
    asyncio.run(main())
