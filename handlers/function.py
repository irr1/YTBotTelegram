import os
import hashlib
import yt_dlp
import time
import cv2
import glob
from aiogram.types import FSInputFile
from telethon.tl.types import DocumentAttributeVideo
from telethon_client import client
import keyboard.inline_kb as in_kb

# Максимальный размер файла для Telegram (50 MB)
MAX_FILE_SIZE = 50 * 1024 * 1024
CACHE_PATH = "cache"  # Папка для кэширования


def generate_url_id(url: str):
    return hashlib.md5(url.encode()).hexdigest()


def get_cookies_file(url):
    if "instagram.com" in url:
        return "cookies_instagram.txt"
    elif "vk.com" in url:
        return "cookies_vk.txt"
    return None


def get_video_metadata(filename):
    cap = cv2.VideoCapture(filename)
    if not cap.isOpened():
        return 0, 0, 0
    frames = cap.get(cv2.CAP_PROP_FRAME_COUNT)
    fps = cap.get(cv2.CAP_PROP_FPS)
    duration = frames / fps if fps else 0
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    cap.release()
    return duration, width, height


def format_duration(duration):
    if duration < 60:
        return f"{int(duration)}с"
    elif duration < 3600:
        minutes, seconds = divmod(duration, 60)
        return f"{int(minutes)}м {int(seconds)}с"
    else:
        hours, minutes = divmod(duration // 60, 60)
        seconds = duration % 60
        return f"{int(hours)}ч {int(minutes)}м {int(seconds)}с"


def get_cache_filename(url, media_type, format_id=None):
    """Генерирует имя файла для кэша на основе URL и формата"""
    url_hash = hashlib.md5(url.encode()).hexdigest()
    if media_type == 'video':
        format_suffix = format_id if format_id else 'best'
        return f"{CACHE_PATH}/{url_hash}_video_{format_suffix}.mp4"
    else:
        return f"{CACHE_PATH}/{url_hash}_audio.mp3"


async def choose_quality(message, url_id, url):
    ydl_opts = {
        'quiet': True,
        'skip_download': True
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)
        formats = info.get('formats', [])

    quality_buttons = []
    for f in formats:
        if f.get('vcodec') != 'none' and f.get('acodec') != 'none':
            format_id = f['format_id']
            height = f.get('height', 'Unknown')
            filesize = f.get('filesize', 0) or 0
            size_mb = round(filesize / (1024 * 1024), 2) if filesize else "Неизвестно"
            cache_filename = get_cache_filename(url, 'video', format_id)
            label = f"{height}p (мгновенно)" if os.path.exists(cache_filename) else f"{height}p ({size_mb} MB)"
            quality_buttons.append([label, f"quality|{url_id}|{format_id}"])

    if not quality_buttons:
        await message.answer("Не удалось получить список качеств. Скачиваю в лучшем качестве...")
        return await download_and_send_media(message.bot, message.chat.id, url, media_type='video')

    await message.answer("Выберите качество видео:", reply_markup=await in_kb.quality_btn(quality_buttons, url_id))


async def download_and_send_media(bot, chat_id, url, media_type, format_id=None):
    cookies_file = get_cookies_file(url)
    output_path = "downloads"
    if not os.path.exists(output_path):
        os.makedirs(output_path)
    if not os.path.exists(CACHE_PATH):
        os.makedirs(CACHE_PATH)

    # Проверяем кэш
    cache_filename = get_cache_filename(url, media_type, format_id)
    if os.path.exists(cache_filename):
        # Используем кэшированный файл
        filename = cache_filename
        info = None  # Метаданные не нужны, если файл уже есть
    else:
        # Скачиваем новый файл
        base_filename = f"media_{int(time.time())}"
        temp_filename = f"{output_path}/{base_filename}.%(ext)s"

        format_choice = {
            "video": "bestvideo+bestaudio/best" if not format_id else format_id,
            "audio": "bestaudio/best"
        }

        ydl_opts = {
            'format': format_choice.get(media_type, 'best'),
            'outtmpl': temp_filename,
            'merge_output_format': 'mp4' if media_type == 'video' else None,
            'n_threads': 8,
            'progress_hooks': [lambda d: print(f"Скачивание: {d.get('_percent_str', '0%')}")],
            'quiet': False,
        }

        if media_type == 'audio':
            ydl_opts['postprocessors'] = [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192'
            }]

        if cookies_file and os.path.exists(cookies_file):
            ydl_opts['cookiefile'] = cookies_file

        start_time = time.time()
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            expected_filename = ydl.prepare_filename(info)
            if media_type == 'audio':
                expected_filename = expected_filename.rsplit('.', 1)[0] + '.mp3'
            elif media_type == 'video':
                expected_filename = expected_filename.rsplit('.', 1)[0] + '.mp4'

        downloaded_files = glob.glob(f"{output_path}/{base_filename}.*")
        if not downloaded_files:
            raise FileNotFoundError(f"Ни один файл не найден в {output_path} с базовым именем {base_filename}!")

        filename = downloaded_files[0]
        if not os.path.exists(filename):
            raise FileNotFoundError(f"Файл {filename} не найден после скачивания!")

        # Копируем файл в кэш
        os.rename(filename, cache_filename)
        filename = cache_filename

    # Собираем метаданные (если файл не из кэша)
    if info:
        title = info.get('title', 'Без названия')
        webpage_url = info.get('webpage_url', url)
        uploader = info.get('uploader', 'Неизвестен')
        upload_date = info.get('upload_date', 'Неизвестна')
        duration = info.get('duration', 0)
        quality = info.get('format', 'Неизвестно') if media_type == 'video' else '192kbps'
    else:
        # Для кэшированных файлов метаданные недоступны без повторного запроса
        title = "Название неизвестно (из кэша)"
        webpage_url = url
        uploader = "Неизвестен (из кэша)"
        upload_date = "Неизвестна (из кэша)"
        duration = get_video_metadata(filename)[0]  # Берем длительность из файла
        quality = format_id if media_type == 'video' and format_id else '192kbps'

    if upload_date and upload_date != 'Неизвестна':
        upload_date = f"{upload_date[:4]}-{upload_date[4:6]}-{upload_date[6:]}"
    duration_str = format_duration(duration)
    resolution = quality if media_type == 'video' else '192kbps'

    # Форматируем сообщение с жирным шрифтом
    if media_type == 'video':
        caption = (
            "*🎥Вот твое видео! Приятного просмотра!*\n\n"
            f"📺 {title}\n"
            f"🔗 {webpage_url}\n"
            f"💁‍♂️ {uploader}\n"
            f"📆 {upload_date}\n"
            f"⏰ {duration_str}\n"
            f"📸 {resolution}\n\n"
            "@download_from_irr1_bot"
        )
    else:
        caption = (
            "*🔉"
            "Вот твое аудио! Приятного прослушивания!*\n\n"
            f"🎧 {title}\n"
            f"🔗 {webpage_url}\n"
            f"💁‍♂️ {uploader}\n"
            f"📆 {upload_date}\n"
            f"⏰ {duration_str}\n"
            f"📸 {resolution}\n\n"
            "@download_from_irr1_bot"
        )

    file_size = os.path.getsize(filename)
    if file_size <= MAX_FILE_SIZE:
        media_file = FSInputFile(filename)
        if media_type == 'video':
            await bot.send_video(chat_id, media_file, caption=caption, parse_mode="Markdown")
        else:
            await bot.send_audio(chat_id, media_file, caption=caption, parse_mode="Markdown")
    else:
        await bot.send_message(chat_id, "Файл больше 50MB, отправляю через Telethon...")
        duration_sec, width, height = get_video_metadata(filename)
        async with client:
            await client.send_file(
                chat_id,
                filename,
                caption=caption,
                force_document=False,
                attributes=[DocumentAttributeVideo(duration=duration_sec, w=width, h=height, supports_streaming=True)]
            )

    # Не удаляем файл из кэша