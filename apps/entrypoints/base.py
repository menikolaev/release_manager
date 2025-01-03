from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from apps.app import App


class BaseEntrypoint:
    def __init__(self, app: 'App'):
        self.app = app
