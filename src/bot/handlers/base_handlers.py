import contextlib
import logging
import time

from aiogram import Router, types
from aiogram.filters import CommandStart
from redis.asyncio import Redis

from bot.controllers.base_conrollers import ban_process, check_spam, hash_message
from bot.internal.replies import answers
from config import settings

router = Router()
redis = Redis(db=5)
logger = logging.getLogger(__name__)


@router.message(CommandStart())
async def start_message(
        message: types.Message,
) -> None:
    await message.answer(
        text=answers['start'],
    )


@router.message()
async def handle_message(message: types.Message):
    if message.from_user.id == settings.ADMIN:
        return

    if message.from_user.full_name in ['Telegram', 'Channel', 'Group']:
        logging.info('Message from Channel or Chat, ignoring...')
        return

    else:
        user_id = message.from_user.id
        key_message = f'user:{user_id}:messages'
        key_group = f'user:{user_id}:groups'
        user_text = message.text
        with contextlib.suppress(AttributeError):
            hash_text = hash_message(user_text)
        banned = await check_spam(message)

        if banned:
            await ban_process(message)
        if hash_text:
            if await redis.sismember(key_message, hash_text):
                await ban_process(message)
            else:
                await redis.sadd(key_group, message.chat.id)
                await redis.sadd(key_message, hash_text)
                await redis.expire(key_message, settings.COOLDOWN_TIME)
