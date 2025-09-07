from typing import Optional
from dataclasses import dataclass

from google.cloud import bigquery
from pinecone import Pinecone
from supabase import Client as SupabaseClient

from src.enums import CatalogScore


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
    catalog_score: Optional[CatalogScore] = None
    days_lookback: Optional[int] = None

    def __post_init__(self):
        if not self.sort_by_date: 
            self.days_lookback = None

    def __repr__(self):
        return (
            f"Config("
            f"sort_by_date={self.sort_by_date}, "
            f"from_interactions={self.from_interactions}, "
            f"from_saved={self.from_saved}, is_women={self.is_women}, "
            f"ascending_saved={self.ascending_saved}, "
            f"catalog_score={self.catalog_score}, "
            f"days_lookback={self.days_lookback}"
            ")"
        )

    def __str__(self):
        return self.__repr__()
