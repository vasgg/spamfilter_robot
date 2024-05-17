import contextlib
import hashlib
import logging
import time

from aiogram import Bot, exceptions, types
from aiogram.exceptions import TelegramAPIError
import aiohttp
from redis.asyncio import Redis

from bot.internal.replies import answers
from config import settings

logger = logging.getLogger(__name__)


async def get_all_chat_ids_from_user(user_id: int, redis: Redis) -> list[int]:
    key = f'user:{user_id}:groups'
    chat_ids = await redis.smembers(key)
    chat_ids = [int(chat_id) for chat_id in chat_ids]
    return chat_ids


async def check_spam(message_text: str, user_id: int, username: str | None) -> bool:
    data = {
        "msg": message_text,
        'user_id':  user_id,
        'user_name': username or ''
    }
    headers = {'Content-Type': 'application/json',
               'Authorization': settings.validator_header}
    async with aiohttp.ClientSession() as session:
        async with session.post(settings.VALIDATOR_URL, json=data, headers=headers) as response:
            response.raise_for_status()
            json_response = await response.json()
            return json_response.get('spam', False)


def hash_message(message: str) -> str:
    return hashlib.sha256(message.encode()).hexdigest()


async def ban_process(message: types.Message, redis: Redis):
    current_time = int(time.time())
    until_date = current_time + settings.BAN_TIME if not settings.PERMANENT_BAN else None
    ban_time_text = answers['forever'] if settings.PERMANENT_BAN else answers['ban_time'].format(settings.BAN_TIME)
    ban_report_text = answers['ban_report_text'].format(message.from_user.full_name, message.chat.title, ban_time_text, message.text)
    permissions = types.ChatPermissions(
        can_send_audios=False,
        can_send_documents=False,
        can_send_photos=False,
        can_send_videos=False,
        can_send_video_notes=False,
        can_send_voice_notes=False,
        can_send_polls=False,
        can_send_other_messages=False,
        can_add_web_page_previews=False,
        can_change_info=False,
        can_invite_users=False,
        can_pin_messages=False,
        can_manage_topics=False,
    )
    await message.bot.send_message(message.chat.id, ban_report_text)
    await message.delete()
    chats = await get_all_chat_ids_from_user(message.from_user.id, redis)
    for chat_id in chats:
        with contextlib.suppress(exceptions.TelegramBadRequest):
            await message.bot.restrict_chat_member(chat_id=chat_id,
                                                   user_id=message.from_user.id,
                                                   permissions=permissions,
                                                   until_date=until_date)
    try:
        await message.bot.send_message(settings.REPORTS_CHAT_ID, ban_report_text)
    except exceptions.TelegramMigrateToChat:
        await message.bot.send_message(settings.REPORTS_CHAT_ID, 'group chat was upgraded to a supergroup chat, '
                                                                 'change REPORTS_CHAT_ID in .env file')
    logger.info(ban_report_text)


async def is_user_admin(bot: Bot, chat_id: int, user_id: int) -> bool:
    try:
        chat_administrators = await bot.get_chat_administrators(chat_id)
        return any(admin.user.id == user_id for admin in chat_administrators)
    except TelegramAPIError:
        logging.exception(f"Error checking if user is admin")
        return False
