import re
from typing import TYPE_CHECKING

from telebot.types import Message

from apps.entrypoints.base import BaseEntrypoint
from apps.services.build_create import BuildRequest

if TYPE_CHECKING:
    from telebot import TeleBot

    from apps.app import App


class TelegramBotEntrypoint(BaseEntrypoint):
    methods = {
        'build': ['build']
    }

    build_regexp = re.compile(r'/build (?P<project_name>[\w\-]*)\s?(?P<branches>[\w\-,\s]*)')

    def __init__(self, app: 'App', bot: 'TeleBot'):
        super().__init__(app)
        self.bot = bot
        self.build_create_service = self.app.composition_root.build_create_service

        for method, commands in self.methods.items():
            self.bot.register_message_handler(commands=commands, callback=getattr(self, method))

    def run(self):
        self.bot.polling()

    def build(self, message: Message):
        """
        Обрабатываем запросы вида: /build admin #1,#2,#3
        где admin - название проекта
        #1 - конкретный MR
        """
        project_name, mrs_order = self.build_regexp.match(message.text).groups()

        build_request = BuildRequest(
            project_name=project_name,
            mrs_order=[x.strip() for x in mrs_order.split(',')] if mrs_order else [],
            major_version=1,
            sprint_number=10,  # Для теста
        )

        result_message = self.build_create_service.create_build(build_request=build_request)

        self.bot.reply_to(message, result_message)
