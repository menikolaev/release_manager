from typing import TYPE_CHECKING

import telebot

from apps.adapters.gitlab import GitlabApi
from apps.entrypoints.telegram import TelegramBotEntrypoint
from apps.services.build_create import BuildCreateService

if TYPE_CHECKING:
    from config.settings import Config

    from apps.app import App


class CompositionRoot:
    def __init__(self, settings: 'Config', app: 'App'):
        self.settings = settings
        self.app = app

        self._dependencies = {}

    def __getattr__(self, item: str):
        return self._dependencies[item]

    def make(self):
        self._dependencies['gitlab_api'] = GitlabApi(settings=self.settings)
        self._dependencies['build_create_service'] = BuildCreateService(build_api=self.gitlab_api)
        self._dependencies['telegram_bot'] = telebot.TeleBot(token=self.settings.telegram_bot_token.get_secret_value())
        self._dependencies['telegram_entrypoint'] = TelegramBotEntrypoint(app=self.app, bot=self.telegram_bot)

