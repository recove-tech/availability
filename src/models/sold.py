from typing import Dict
from dataclasses import dataclass
from datetime import datetime


@dataclass
class SoldItem:
    id: str

    def __post_init__(self):
        self.updated_at = datetime.now().isoformat()

    def to_dict(self) -> Dict:
        return {
            "vinted_id": self.id,
            "updated_at": self.updated_at,
        }