from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    data_dir: str = "./data"
    temp_data_dir: str = "./tempData"
    store_dir: str = "./store"
    title: str = "Hi-CService"
    use_storage: bool = False
    allow_uploads: bool = True

    class Config:
        env_file = ".env"
