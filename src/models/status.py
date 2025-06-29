from typing import Dict, Optional
from dataclasses import dataclass


@dataclass
class VintedItemStatus:
    item_id: str
    is_available: bool
    status_code: int
    error: Optional[str] = None

    def to_dict(self) -> Dict:
        return {
            "item_id": self.item_id,
            "is_available": self.is_available,
            "status_code": self.status_code,
            "error": self.error,
        }

    @property
    def ok(self) -> bool:
        return self.status_code == 200
