from typing import List, Iterator, Dict, Optional
from dataclasses import dataclass, field

from random import random
from pinecone import ScoredVector


@dataclass
class PineconeEntry:
    id: str
    point_id: str
    vinted_id: str
    url: str
    category_type: Optional[str] = None
    created_at: Optional[str] = None

    @classmethod
    def from_vector(cls, vector: ScoredVector) -> "PineconeEntry":
        metadata = vector.metadata

        return cls(
            id=vector.metadata["id"],
            point_id=vector.id,
            vinted_id=vector.metadata["vinted_id"],
            url=vector.metadata["url"],
            category_type=metadata.get("category_type"),
            created_at=metadata.get("created_at"),
        )

    @classmethod
    def from_dict(cls, data: Dict) -> "PineconeEntry":
        return cls(
            id=data["id"],
            point_id=data["point_id"],
            vinted_id=data["vinted_id"],
            url=data["url"],
            category_type=data.get("category_type"),
            created_at=data.get("created_at"),
        )


@dataclass
class PineconeDataLoader:
    entries: List[PineconeEntry] = field(default_factory=list)

    def add(self, entry: PineconeEntry) -> None:
        self.entries.append(entry)

    def __iter__(self) -> Iterator[PineconeEntry]:
        return iter(self.entries)

    def __len__(self) -> int:
        return len(self.entries)

    def __getitem__(self, index: int) -> PineconeEntry:
        return self.entries[index]

    @property
    def total_rows(self) -> int:
        return len(self.entries)

    @property
    def vinted_ids(self) -> List[str]:
        return [entry.vinted_id for entry in self.entries]
