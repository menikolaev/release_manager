from typing import TYPE_CHECKING

from apps.composition_root import CompositionRoot

if TYPE_CHECKING:
    from config.settings import Config


class App:
    def __init__(self, settings: 'Config'):
        self.settings = settings
        self.composition_root = CompositionRoot(settings=settings, app=self)
        self.composition_root.make()

    def run(self):
        self.composition_root.telegram_entrypoint.run()
