import os

from aiogram import Bot

from config import settings


async def on_startup_notify(bot: Bot):
    current_directory = os.getcwd()
    await bot.send_message(
        settings.ADMIN,
        f'{current_directory.split("/")[-1]} started\n\n/start',
        disable_notification=True,
    )


async def on_shutdown_notify(bot: Bot):
    current_directory = os.getcwd()
    await bot.send_message(
        settings.ADMIN,
        f'{current_directory.split("/")[-1]} started\n\n/start',
        disable_notification=True,
    )
