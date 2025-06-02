from typing import List, Iterator, Dict, Literal, Optional
from dataclasses import dataclass, field
from enum import Enum

from random import random
from google.cloud import bigquery
from pinecone import Pinecone, ScoredVector
from supabase import Client
from selenium.webdriver.chrome.webdriver import WebDriver

from .bigquery import get_job_index
from .vinted.client import Vinted


RunnerMode = Literal["api", "driver"]


class ItemStatus(Enum):
    AVAILABLE = "available"
    SOLD = "sold"
    NOT_FOUND = "not_found"
    UNKNOWN = "unknown"


@dataclass
class JobConfig:
    bq_client: bigquery.Client
    pinecone_index: Pinecone.Index
    vinted_client: Vinted
    only_top_brands: bool
    only_vintage_dressing: bool
    sort_by_likes: bool
    sort_by_date: bool
    from_interactions: bool
    from_saved: bool
    is_women: bool
    ascending_saved: bool
    driver: Optional[WebDriver] = None
    supabase_client: Optional[Client] = None

    def __post_init__(self):
        if self.only_vintage_dressing and self.only_top_brands:
            if random() < 0.5:
                self.only_vintage_dressing = False
            else:
                self.only_top_brands = False

        if self.sort_by_date and self.sort_by_likes:
            if random() < 0.5:
                self.sort_by_date = False
            else:
                self.sort_by_likes = False

        self._get_id()
        self.set_index()

    def __repr__(self):
        return (
            f"Config(id={self.id}, index={self.index}, "
            f"only_top_brands={self.only_top_brands}, "
            f"only_vintage_dressing={self.only_vintage_dressing}, "
            f"sort_by_likes={self.sort_by_likes}, "
            f"sort_by_date={self.sort_by_date}, "
            f"from_interactions={self.from_interactions}, "
            f"from_saved={self.from_saved}, is_women={self.is_women}, "
            f"ascending_saved={self.ascending_saved})"
        )

    def __str__(self):
        return self.__repr__()

    def set_index(self, index: Optional[int] = None):
        if self.index is None:
            if index is None:
                self.index = get_job_index(self.bq_client, self.id)
            else:
                self.index = index

    def _get_id(self):
        self.index = 0

        if self.from_interactions:
            self.id = "interactions"
        elif self.only_top_brands:
            self.id = "top_brands"
        elif self.only_vintage_dressing:
            self.id = "vintage_dressing"
        elif self.from_saved:
            self.id = f"saved_{self.ascending_saved}"
            self.index = None
        else:
            self.id = "all"

        if self.sort_by_likes:
            self.id += "_likes"
        elif self.sort_by_date:
            self.id += "_date"

        if not self.from_saved:
            if self.is_women is not None:
                self.id += f"_women_{self.is_women}"

        self.id = self.id.lower()


@dataclass
class PineconeEntry:
    id: str
    point_id: str
    vinted_id: str
    url: str
    category_type: Optional[str] = None

    @classmethod
    def from_vector(cls, vector: ScoredVector) -> "PineconeEntry":
        metadata = vector.metadata

        return cls(
            id=vector.metadata["id"],
            point_id=vector.id,
            vinted_id=vector.metadata["vinted_id"],
            url=vector.metadata["url"],
            category_type=metadata.get("category_type"),
        )

    @classmethod
    def from_dict(cls, data: Dict) -> "PineconeEntry":
        return cls(
            id=data["id"],
            point_id=data["point_id"],
            vinted_id=data["vinted_id"],
            url=data["url"],
            category_type=data.get("category_type"),
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
