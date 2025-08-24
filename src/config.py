from typing import Dict, Tuple, Optional, List

import random

from google.cloud import bigquery
from pinecone import Pinecone
from supabase import Client as SupabaseClient

from .models import Config
from .bigquery import init_bigquery_client
from .supabase import init_supabase_client
from .enums import PINECONE_INDEX_NAME, CATALOG_SCORE_VALUES
from .utils import select_weighted_value


def init_clients(
    secrets: Dict, with_supabase: bool = False
) -> Tuple[bigquery.Client, Pinecone.Index, Optional[SupabaseClient]]:
    gcp_credentials = secrets.get("GCP_CREDENTIALS")
    bq_client = init_bigquery_client(credentials_dict=gcp_credentials)

    pinecone_client = Pinecone(api_key=secrets.get("PINECONE_API_KEY"))
    pinecone_index = pinecone_client.Index(PINECONE_INDEX_NAME)

    if with_supabase:
        supabase_client = init_supabase_client(
            url=secrets.get("SUPABASE_URL"),
            key=secrets.get("SUPABASE_SERVICE_ROLE_KEY"),
        )
    else:
        supabase_client = None

    return bq_client, pinecone_index, supabase_client


def init_config(
    bq_client: bigquery.Client,
    pinecone_index: Pinecone.Index,
    supabase_client: Optional[SupabaseClient] = None,
    sort_by_date_alpha: float = 0.0,
    is_women_alpha: float = 0.0,
    saved_ascending_alpha: float = 0.0,
    from_interactions: bool = False,
    from_saved: bool = False,
    catalog_score_weights: Optional[List[float]] = None,
    days_lookback: Optional[int] = None,
) -> Config:
    if from_saved:
        if not supabase_client:
            raise ValueError("Supabase client is required for from_saved mode")

        if from_interactions:
            raise ValueError("from_interactions is not supported for from_saved mode")

    sort_by_date = random.random() < sort_by_date_alpha
    is_women = random.random() < is_women_alpha
    ascending_saved = random.random() < saved_ascending_alpha

    if catalog_score_weights is not None:
        catalog_score = select_weighted_value(
            values=CATALOG_SCORE_VALUES,
            weights=catalog_score_weights,
        )
    else:
        catalog_score = None

    config = Config(
        bq_client=bq_client,
        supabase_client=supabase_client,
        pinecone_index=pinecone_index,
        sort_by_date=sort_by_date,
        from_interactions=from_interactions,
        from_saved=from_saved,
        is_women=is_women,
        ascending_saved=ascending_saved,
        catalog_score=catalog_score,
        days_lookback=days_lookback,
    )

    return config
