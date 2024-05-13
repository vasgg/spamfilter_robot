import json
import os

import pytest
from aioresponses import aioresponses, CallbackResult

from bot.controllers.base_conrollers import check_spam
from config import settings


@pytest.mark.asyncio
async def test_check_spam():
    msg_text = "abacaba"
    user_id = 100500
    username = "some_user_name"

    def callback(_, **kwargs):
        assert kwargs['data'] == {'msg': msg_text, 'user_id': user_id, 'user_name': username}
        assert kwargs['headers']['Authorization'] == settings.validator_header
        return CallbackResult(status=200, body=json.dumps({"spam": True}))

    with aioresponses() as m:
        m.post(os.environ["VALIDATOR_URL"], callback=callback)
        res = await check_spam(msg_text, user_id, username)

    assert res is True


@pytest.mark.asyncio
async def test_check_spam():
    msg_text = "abacaba"
    user_id = 100500
    username = "some_user_name"
    res = await check_spam(msg_text, user_id, username)
    print(res)