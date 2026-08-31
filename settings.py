from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    data_dir: str = "./data"
    store_dir: str = "./store"
    title: str = "Hi-CService"
    use_storage: bool = False

    class Config:
        env_file = ".env"
