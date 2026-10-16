from pathlib import Path
from fastapi import HTTPException
from typing import Tuple
from cooler_file import CoolFile


class DataStore():
    def __init__(self, directory):
        self.data_dir = directory
        self.datasets: dict[str, CoolFile] = dict()
        self.dataset_groups: dict[str, str] = dict()
        self.groups: list[tuple[str, str]] = []
        self.load_groups()
        self.fetch_datasets()

    def load_groups(self):
        groups_file = Path(__file__).parent / "groups.txt"
        if not groups_file.is_file():
            return
        for line in groups_file.read_text(encoding="utf-8", errors="ignore").splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            parts = line.split()
            if len(parts) > 1:
                self.groups.append((parts[0].lower(), parts[1]))

    def get_group_from_pw(self, password):
        for group, group_password in self.groups:
            if password == group_password:
                return group
        return None

    def free_upload_path(self, stem: str, suffix: str) -> Path:
        target_dir = Path(self.data_dir).resolve()
        target_dir.mkdir(parents=True, exist_ok=True)

        base, counter = stem, 1
        while True:
            target = (target_dir / f"{base}{suffix}").resolve()
            if target.parent != target_dir:
                raise HTTPException(status_code=400, detail="The uploaded file name is not usable.")
            if base not in self.datasets and not target.exists():
                return target
            counter += 1
            base = f"{stem}_{counter}"

    def record_group(self, identifier: str, group: str):
        group_file = Path(self.data_dir) / f"{group}.txt"
        existing = group_file.read_text(encoding="utf-8", errors="ignore") if group_file.is_file() else ""
        listed = [line.strip().lower() for line in existing.splitlines() if line.strip() and not line.strip().startswith("#")]
        if identifier.lower() in listed:
            return
        with group_file.open("a", encoding="utf-8") as f:
            f.write(f"{identifier}\n")

    def register(self, dataset: CoolFile, group: str | None = None) -> tuple[CoolFile, str | None]:
        identifier = dataset.get_identifier()
        self.datasets[identifier] = dataset
        if group is not None:
            try:
                self.record_group(identifier, group)
            except OSError as error:
                del self.datasets[identifier]
                raise HTTPException(status_code=500, detail=f"The dataset could not be recorded as belonging to group {group}: {error}")
            self.dataset_groups[identifier] = group
        return dataset, None

    def fetch_datasets(self):
        dataset_groups_temp = dict()
        for file in Path(self.data_dir).iterdir():
            filename = file.name.lower()
            if not file.is_file() or not filename.endswith(".txt"):
                continue
            group = filename.split(".")[0]
            if group not in [group[0] for group in self.groups]:
                continue
            
            for line in file.read_text(encoding="utf-8", errors="ignore").splitlines():
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                dataset_groups_temp[line.lower()] = group
        
        for file in Path(self.data_dir).iterdir():
            filename = file.name
            if filename.endswith(".cool") or filename.endswith(".mcool"):
                dataset = CoolFile(file)
                dataset_name = filename.lower().split(".")[0]
                if (dataset_groups_temp.get(dataset_name)):
                    self.dataset_groups[dataset.get_identifier()] = dataset_groups_temp[dataset_name]
                self.datasets[dataset.get_identifier()] = dataset
        print(self.dataset_groups)

    def is_visible(self, identifier: str, group: str | None) -> bool:
        dataset_group = self.dataset_groups.get(identifier)
        return dataset_group is None or dataset_group == group

    def get_dataset_ids(self, group: str | None = None):
        return [identifier for identifier in self.datasets if self.is_visible(identifier, group)]

    def get_dataset(self, identifier: str, group: str | None = None):
        return self.datasets.get(identifier, group)

    def get_dataset_info(self, identifier: str, group: str | None = None):
        return self.get_dataset(identifier, group).get_info()

class TempDataStore(DataStore):
    def __init__(self, directory):
        super().__init__(directory)

    def register(self, dataset: CoolFile, group: str | None = None):
        identifier = dataset.get_identifier()
        self.datasets[identifier] = dataset
        if group is not None:
            try:
                self.record_group(identifier, group)
            except OSError as error:
                del self.datasets[identifier]
                raise HTTPException(status_code=500, detail=f"The dataset could not be recorded as belonging to group {group}: {error}")
            self.dataset_groups[identifier] = group
        print(self.datasets)
        return dataset, None

    def fetch_datasets(self):
        print("Fetching temp datasets")
        # TODO: Instead of fetching datasets, remove all from the data directory
        pass

class DataManager:
    data_store: DataStore
    temp_data_store = TempDataStore

    def __init__(self, settings):
        self.data_store = DataStore(settings.data_dir)
        self.temp_data_store = TempDataStore(settings.temp_data_dir)

    def get_group_from_pw(self, password):
        group = self.data_store.get_group_from_pw(password)
        if not group:
            group = self.temp_data_store.get_group_from_pw(password)
        return group

    def find_free_filename(self, stem: str, suffix: str, temporary: bool) -> Path:
        if temporary:
            return self.temp_data_store.free_upload_path(stem + "Temp", suffix)
        else:
            return self.data_store.free_upload_path(stem, suffix)

    def register(self, filepath: Path, group: str | None = None, temporary: bool = True) -> Tuple[CoolFile, str | None]:
        try:
            dataset = CoolFile(filepath)
            dataset.verify()
        except Exception as error:
            filepath.unlink(missing_ok=True)
            raise HTTPException(status_code=400, detail=f"The uploaded file could not be read as a Hi-C cooler file: {error}")

        if temporary:
            return self.temp_data_store.register(dataset, group)
        else:
            return self.data_store.register(dataset, group)

    def get_dataset_ids(self, group: str | None = None):
        return self.data_store.get_dataset_ids(group) + self.temp_data_store.get_dataset_ids(group)

    def get_dataset(self, identifier: str, group: str | None = None):
        dataset = self.data_store.get_dataset(identifier, group)
        if not dataset:
            dataset = self.temp_data_store.get_dataset(identifier, group)
        if dataset is None:
            raise HTTPException(status_code=404, detail=f"Dataset with identifier {identifier} not found.")
        return dataset

    def get_dataset_info(self, identifier: str, group: str | None = None):
        return self.get_dataset(identifier, group).get_info()