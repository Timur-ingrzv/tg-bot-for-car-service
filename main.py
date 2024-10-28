import asyncio
from aiogram import Dispatcher, Bot, types
from aiogram.filters.command import Command


bot = Bot(token="7813099217:AAHE_Bf60OfAMigeVeoimJHp_Zy5umhiK28")
dp = Dispatcher()

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer(f"Добро пожаловать!")

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
