from pydantic import field_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    data_dir: str = "./data"
    temp_data_dir: str = "./tempData"
    store_dir: str = "./store"
    title: str = "Hi-CService"
    use_storage: bool = False
    allow_uploads: bool = True

    max_upload_mb: int = 9192
    max_filename_length: int = 128
    allowed_origins: str = ""

    clamd_host: str | None = None
    clamd_port: int = 3310
    clamd_socket: str | None = None
    scan_timeout_seconds: int = 120

    @field_validator("max_upload_mb", "max_filename_length")
    @classmethod
    def reject_unusable_limits(cls, value: int) -> int:
        # Zero or less would refuse every file, and a negative limit would do so with a message
        # about the file being over a limit of minus two million bytes.
        if value <= 0:
            raise ValueError("has to be a positive number")
        return value

    @property
    def allowed_origin_patterns(self) -> list[str]:
        """The ALLOWED_ORIGINS setting split into the list the upload check compares against."""
        return [pattern.strip().lower() for pattern in self.allowed_origins.split(",") if pattern.strip()]

    class Config:
        env_file = ".env"
