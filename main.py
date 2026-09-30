# Patch distutils for Python 3.12+ compatibility (must be first!)
import distutils_fix

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware


from settings import Settings
from api import create_api
from data_manager import DataManager
from data_store import ReconstructionDataStore

settings: Settings = Settings()
data_manager = DataManager(settings)
storage_manager = ReconstructionDataStore(settings)

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

create_api(app, settings, data_manager, storage_manager)


# Run by using fastapi dev in the python env terminal
if __name__ == '__main__':
    print('Henlo')

# See PyCharm help at https://www.jetbrains.com/help/pycharm/
