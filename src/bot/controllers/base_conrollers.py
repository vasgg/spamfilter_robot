import contextlib
import hashlib
import time

from aiogram import exceptions, types
import aiohttp

from bot.handlers.base_handlers import logger, redis
from bot.internal.replies import answers
from config import settings


async def get_all_chat_ids_from_user(user_id: int) -> list[int]:
    key = f'user:{user_id}:groups'
    chat_ids = await redis.smembers(key)
    chat_ids = [int(chat_id) for chat_id in chat_ids]
    return chat_ids


async def check_spam(message: types.Message) -> bool:
    data = message.model_dump_json(exclude_unset=True)
    headers = {'Content-Type': 'application/json'}
    async with aiohttp.ClientSession() as session:
        async with session.post(settings.VALIDATOR_URL, data=data, headers=headers) as response:
            if response.status == 200:
                json_response = await response.json()
                return json_response.get('result', False)
            else:
                raise AssertionError(f'Failed to validate message. Status code: {response.status}')


def hash_message(message: str) -> str:
    return hashlib.sha256(message.encode()).hexdigest()


async def ban_process(message):
    current_time = int(time.time())
    until_date = current_time + settings.BAN_TIME if not settings.PERMANENT_BAN else None
    banned_text = answers['banned_text']
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
    with contextlib.suppress(exceptions.TelegramBadRequest):
        try:
            await message.bot.send_message(message.from_user.id, banned_text + ban_time_text)
            await message.delete()
            chats = await get_all_chat_ids_from_user(message.from_user.id)
            for chat_id in chats:
                with contextlib.suppress(exceptions.TelegramBadRequest):
                    await message.bot.restrict_chat_member(chat_id=chat_id,
                                                           user_id=message.from_user.id,
                                                           permissions=permissions,
                                                           until_date=until_date)
            await message.bot.send_message(settings.REPORTS_CHAT_ID, ban_report_text)
        except exceptions.TelegramMigrateToChat:
            await message.bot.send_message(settings.REPORTS_CHAT_ID, 'group chat was upgraded to a supergroup chat, '
                                                                     'change REPORTS_CHAT_ID in .env file')
    logger.info(ban_report_text)
