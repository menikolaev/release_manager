from apps.app import App
from config.settings import Config


def main():
    settings = Config()
    App(settings=settings).run()


if __name__ == '__main__':
    main()
