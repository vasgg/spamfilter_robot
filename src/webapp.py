from random import choices
import logging
from fastapi import FastAPI

app = FastAPI()
logger = logging.getLogger(__name__)


@app.post("/validate/")
def should_be_banned(input_data: dict):
    result = choices([True, False], weights=(10, 90))[0]
    logger.info(f'{input_data}, {result}')
    return {"result": result}
