import logging
from aiogram import BaseMiddleware
from aiogram.types import Message


logging.basicConfig(filename='../bot_commands.log', level=logging.INFO)

class CommandLoggingMiddleware(BaseMiddleware):
    async def __call__(self, handler, event: Message, data):
        if event.text.startswith('/'):
            logging.info(f"Command: {event.text} from {event.from_user.id}")
        return await handler(event, data)


class CheckFillProfileMiddleware(BaseMiddleware):
    def __init__(self, db):
        self.db = db

    async def __call__(self, handler, event: Message, data):
        state = data.get('state')
        is_fill_profile = await state.get_value('is_fill_profile', False)
        if not is_fill_profile:
            await event.answer("Для начала работы введите /set_profile")
            return

        data['profile'] =  self.db[event.from_user.id]

        return await handler(event, data)