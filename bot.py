import asyncio
import os
from telethon_client import client

from aiogram import Bot, Dispatcher
from dotenv import load_dotenv

from handlers import callback, commands


async def main():
    print("Загрузка .env...")
    load_dotenv()

    token = os.getenv('BOT_TOKEN')
    if not token:
        print("Ошибка: BOT_TOKEN не найден!")
        return

    bot = Bot(token)
    dp = Dispatcher()

    print("Запускаю Telethon...")
    await client.start()
    print("Telethon запущен!")

    if not os.path.exists("downloads"):
        os.makedirs("downloads")

    dp.include_router(commands.router)
    dp.include_router(callback.router)

    print("Bot Start")
    await dp.start_polling(bot)

    while True:
        await asyncio.sleep(1)


if __name__ == '__main__':
    print("Запуск бота...")
    try:
        asyncio.run(main())
    except Exception as e:
        print(f"Ошибка при запуске: {e}")
    except KeyboardInterrupt:
        print("Выход")
