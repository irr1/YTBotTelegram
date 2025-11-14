from aiogram import Bot, Router, F
from aiogram.types import CallbackQuery

from handlers.function import download_and_send_media, choose_quality
import url_storage as storage

router = Router()

@router.callback_query(lambda callback: 'video' in callback.data or 'audio' in callback.data)
async def format_selection(callback: CallbackQuery, bot: Bot):
    storage.url_storage = storage.load_url_storage()
    action, url_id = callback.data.split("|")
    url = storage.url_storage.get(url_id)
    if not url:
        await callback.answer("Ошибка: URL не найден! ⛔️")
        return
    await callback.answer("Подтверждено! ✅")
    if action == 'video':
        await callback.message.answer("Выбираю качество видео... ⭐️")
        await choose_quality(callback.message, url_id, url)
    elif action == 'audio':
        await callback.message.answer("Начинаю загрузку аудио в лучшем качестве... ☄️")
        await download_and_send_media(bot, callback.message.chat.id, url, media_type='audio')

@router.callback_query(lambda callback: callback.data.startswith("quality|"))
async def quality_selected(callback: CallbackQuery, bot: Bot):
    storage.url_storage = storage.load_url_storage()
    _, url_id, format_id = callback.data.split("|")
    url = storage.url_storage.get(url_id)

    if not url:
        await callback.answer("Ошибка: URL не найден! ⛔️")
        return

    await callback.answer("Качество выбрано! ✨")
    await callback.message.answer(f"Начинаю загрузку видео в выбранном качестве... 🏃‍♂️")
    await download_and_send_media(bot, callback.message.chat.id, url, media_type='video', format_id=format_id)