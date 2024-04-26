import logging

from aiogram import F, Router, types
from aiogram.filters import CommandStart
from redis.asyncio import Redis

from bot.controllers.base_conrollers import ban_process, check_spam, hash_message
from bot.internal.replies import answers
from config import settings

router = Router()
logger = logging.getLogger(__name__)


@router.message(CommandStart())
async def start_message(
        message: types.Message,
) -> None:
    await message.answer(
        text=answers['start'],
    )


@router.message(F.text)
async def handle_message(message: types.Message, redis: Redis) -> None:
    if message.from_user.id in settings.WHITELIST:
        logging.info('User in whitelist, ignoring...')
        return

    if message.from_user.full_name in ['Telegram', 'Channel', 'Group']:
        logging.info('Message from Channel or Chat, ignoring...')
        return

    else:
        user_id = message.from_user.id
        key_message = f'user:{user_id}:messages'
        key_group = f'user:{user_id}:groups'
        user_text = message.text
        hash_text = hash_message(user_text)
        banned = await check_spam(message)

        if banned:
            await ban_process(message, redis)
            return
        if await redis.sismember(key_message, hash_text):
            await ban_process(message, redis)
        else:
            await redis.sadd(key_group, message.chat.id)
            await redis.sadd(key_message, hash_text)
            await redis.expire(key_message, settings.COOLDOWN_TIME)
