from pathlib import Path
from fastapi import HTTPException

from cooler_file import CoolFile


class DataManager:
    data_dir = ""
    datasets: dict[str, CoolFile] = dict()
    dataset_groups: dict[str, str] = dict()
    groups: list[tuple[str, str]] = []

    def __init__(self, settings):
        self.data_dir = settings.data_dir
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
        print(self.groups)

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

    def register(self, filepath: Path, group: str | None = None):
        try:
            dataset = CoolFile(filepath)
            dataset.verify()
        except Exception as error:
            filepath.unlink(missing_ok=True)
            raise HTTPException(status_code=400, detail=f"The uploaded file could not be read as a Hi-C cooler file: {error}")
        self.datasets[dataset.get_identifier()] = dataset
        if group is not None:
            self.dataset_groups[dataset.get_identifier()] = group
        return dataset

    def fetch_datasets(self):
        dataset_groups_temp = dict()
        for file in Path(self.data_dir).iterdir():
            filename = file.name.lower()
            if not file.is_file() or not filename.endswith(".txt"):
                continue
            group = filename.split(".")[0]
            print("Group:", group)
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
        dataset = self.datasets.get(identifier)
        if dataset is None:
            raise HTTPException(status_code=404, detail=f"Dataset with identifier {identifier} not found.")
        if not self.is_visible(identifier, group):
            raise HTTPException(status_code=403, detail=f"Dataset with identifier {identifier} is not available for group {group}.")
        return dataset

    def get_dataset_info(self, identifier: str, group: str | None = None):
        return self.get_dataset(identifier, group).get_info()