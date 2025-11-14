from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import Message

import keyboard.inline_kb as in_kb
import handlers.function as hf
import url_storage as storage

router = Router()

@router.message(CommandStart())
async def cmd_start(message: Message):
    await message.reply("Привет! Скинь мне ссылку на видео из ЮТ, ТТ, Инсты или ВК и я помогу тебе скачать его ❤️‍🔥")

@router.message(lambda message: "tiktok.com" in message.text or "youtube.com" in message.text or "youtu.be" in message.text or "instagram.com" in message.text or "vk.com" in message.text)
async def video_request(message: Message):
    url = message.text.strip()
    url_id = hf.generate_url_id(url)
    storage.url_storage[url_id] = url
    storage.save_url_storage(storage.url_storage)
    storage.url_storage = storage.load_url_storage()
    await message.answer("🔥 Выберите формат загрузки:", reply_markup=await in_kb.format_btn(url_id))