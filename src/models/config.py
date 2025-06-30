from typing import Optional
from dataclasses import dataclass

from google.cloud import bigquery
from pinecone import Pinecone
from supabase import Client as SupabaseClient

from src.bigquery import get_job_index


@dataclass
class Config:
    bq_client: bigquery.Client
    pinecone_index: Pinecone.Index
    sort_by_date: bool
    from_interactions: bool
    from_saved: bool
    is_women: bool
    ascending_saved: bool
    supabase_client: Optional[SupabaseClient] = None

    def __post_init__(self):
        self._get_id()
        self.set_index()

    def __repr__(self):
        return (
            f"Config(id={self.id}, index={self.index}, "
            f"sort_by_date={self.sort_by_date}, "
            f"from_interactions={self.from_interactions}, "
            f"from_saved={self.from_saved}, is_women={self.is_women}, "
            f"ascending_saved={self.ascending_saved})"
        )

    def __str__(self):
        return self.__repr__()

    def set_index(self, index: Optional[int] = None):
        if index is None:
            self.index = get_job_index(self.bq_client, self.id)
        else:
            self.index = index

    def _get_id(self):
        self.index = 0

        if self.from_interactions:
            self.id = "interactions"
        elif self.from_saved:
            self.id = f"saved_{self.ascending_saved}"
            self.index = None
        else:
            self.id = "all"

        if self.sort_by_date:
            self.id += "_date"

        if not self.from_saved:
            if self.is_women is not None:
                self.id += "_women" if self.is_women else "_men"

        self.id = self.id.lower()
