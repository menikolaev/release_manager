from pydantic import BaseSettings, AnyHttpUrl, SecretStr


class Config(BaseSettings):
    host: str
    port: str
    gitlab_host: AnyHttpUrl
    gitlab_token: SecretStr
    ref_branch: str
    telegram_bot_token: SecretStr

    class Config:
        env_file = '.env'
        env_file_encoding = 'utf-8'
