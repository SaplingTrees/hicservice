# hicservice

A python fastapi server used for serving tiled Hi-C (cooler) data and preprocess them.

## Install

```bash
python -m venv .venv
.venv\Scripts\activate        # Windows
source .venv/bin/activate     # Linux / macOS
pip install -r requirements.txt
```

Graphviz must be installed on the system (not via pip) — `graph_layouting.py` uses it to lay out graphs.

## Setup `.env`

Create a `.env` file in the project root (it is gitignored):

```
TITLE="Hi-CService"
DATA_DIR=""
TEMP_DATA_DIR=""
STORE_DIR=""
USE_STORAGE=True/False
```

| Key | Meaning |
| --- | --- |
| `DATA_DIR` | Folder holding the `.mcool` / `.cool` files that get served. |
| `TEMP_DATA_DIR` | Where uploads the caller asked not to be kept are written. Defaults to `./tempData`, is created for you, and is emptied of cooler files on every start. |
| `STORE_DIR` | Where calculated 2D graphs and 3D reconstructions are cached. Create this folder yourself, only the `2d` and `3d` subfolders inside it are made for you. |
| `TITLE` | Name of the service. |
| `USE_STORAGE` | Reuse already calculated results from `STORE_DIR` instead of recalculating them. |
| `ALLOW_UPLOADS` | Accept the `/upload` endpoint at all. |
| `MAX_UPLOAD_MB` | Largest accepted upload, counted from the bytes that actually arrive. Defaults to `2048`. |
| `MAX_FILENAME_LENGTH` | Longest accepted file name. Defaults to `128`. |
| `ALLOWED_ORIGINS` | Sites allowed to upload from a browser, comma separated, e.g. `https://chromograph.example.com,http://localhost:*`. `*` matches part of an address. Empty (the default) accepts any site; `*` on its own says so explicitly. |


## Run

```bash
fastapi dev main.py
# or: uvicorn main:app --reload
```

The API is on `http://localhost:8000`, interactive docs on `http://localhost:8000/docs`.

To use it from Chromograph, set `VITE_API_ENDPOINT=http://localhost:8000/` in `chromograph/frontend/.env`.

## Data

Nothing to register — when `DATA_DIR` points at a folder of Hi-C files, all `.mcool` and `.cool` files in it are loaded on startup and served under their filename without extension (`Arabidopsis.mcool` → `/datasets`, `/info/Arabidopsis`). Drop a file in the folder and restart the server to see it.

Datasets are public unless a `<group>.txt` file in `DATA_DIR` lists them; groups and their passcodes come from `groups.txt` (`group_name password` per line).

## Docker

```bash
DATA_DIR="" docker compose up --build
```

`docker compose -f docker-compose.dev.yml up` additionally mounts the source and reloads on change.
