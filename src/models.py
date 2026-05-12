from dataclasses import dataclass, field
from dataclasses_json import dataclass_json
from pathlib import Path
from typing import Optional
from enum import Enum
import json
import uuid


DEFAULT_META_FILE = Path("meta.json")


class Platform(Enum):
    ARK = "ark"
    IRIS = "iris"
    RETINA = "retina"


@dataclass_json
@dataclass
class ExperimentMeta:
    id: str
    data_file: str
    platform: Platform
    created_at: str
    ended_at: Optional[str]
    date_range: tuple[str, str]


@dataclass
class Meta:
    file: Path = field(default_factory=lambda: DEFAULT_META_FILE)
    experiments: dict[str, ExperimentMeta] = field(default_factory=dict)

    def __post_init__(self):
        self.file = Path(self.file)
        if self.file.exists():
            with open(self.file) as f:
                data = json.load(f)
            self.experiments = {k: ExperimentMeta.from_dict(v) for k, v in data.get("experiments", {}).items()}
        else:
            self.save()

    def save(self) -> None:
        with open(self.file, "w") as f:
            json.dump({"experiments": {k: v.to_dict() for k, v in self.experiments.items()}}, f, indent=2)

    def add_experiment(self, experiment: ExperimentMeta) -> str:
        self.experiments[experiment.id] = experiment
        self.save()
        return experiment.id

    def get_experiment(self, id: str) -> Optional[ExperimentMeta]:
        return self.experiments.get(id)

    def remove_experiment(self, id: str) -> None:
        self.experiments.pop(id, None)
        self.save()

    def list_experiments(self) -> list[ExperimentMeta]:
        return list(self.experiments.values())

    @staticmethod
    def new_id() -> str:
        return str(uuid.uuid4())
