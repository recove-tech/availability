from typing import List, Dict, Union, Optional

from google.oauth2 import service_account
from google.cloud import bigquery

from .models import SoldItem
from .enums import *


def init_bigquery_client(credentials_dict: Dict) -> bigquery.Client:
    credentials_dict["private_key"] = credentials_dict["private_key"].replace(
        "\\n", "\n"
    )

    credentials = service_account.Credentials.from_service_account_info(
        credentials_dict
    )

    return bigquery.Client(
        credentials=credentials, project=credentials_dict["project_id"]
    )


def insert_rows_json(client: bigquery.Client, item_ids: List[str]) -> bool:
    try:
        rows = [SoldItem(vinted_id).to_dict() for vinted_id in item_ids]

        errors = client.insert_rows_json(
            table=f"{VINTED_DATASET_ID}.{SOLD_TABLE_ID}",
            json_rows=rows,
        )

        return not errors

    except Exception as e:
        print(e)
        return False


def run_query(
    client: bigquery.Client, query: str, to_list: bool = True
) -> Union[List[Dict], bigquery.table.RowIterator]:
    job_config = bigquery.QueryJobConfig(use_query_cache=True)
    query_job = client.query(query, job_config=job_config)
    results = query_job.result()

    if to_list:
        return [dict(row) for row in results]
    else:
        return results


def query_items(
    sort_by_date: bool = False,
    item_ids: Optional[List[str]] = None,
    n: Optional[int] = None,
    is_women: Optional[bool] = None,
    catalog_score: Optional[CatalogScore] = None,
) -> str:
    where_prefix = "\nAND"

    query = f"""
SELECT item.id, p.point_id, item.vinted_id, item.url, item.category_type, c.score
FROM `{PROJECT_ID}.{VINTED_DATASET_ID}.{ITEM_ACTIVE_TABLE_ID}` item
INNER JOIN `{PROJECT_ID}.{VINTED_DATASET_ID}.{PINECONE_TABLE_ID}` AS p ON item.id = p.item_id
INNER JOIN `{PROJECT_ID}.{VINTED_DATASET_ID}.{CATALOG_TABLE_ID}` AS c USING (catalog_id)
LEFT JOIN `{PROJECT_ID}.{VINTED_DATASET_ID}.{SOLD_TABLE_ID}` AS s USING (vinted_id)
WHERE s.vinted_id IS NULL
    """

    if catalog_score is not None:
        query += f"{where_prefix} c.score = {catalog_score}"

    if is_women is not None:
        query += f"{where_prefix} women = {is_women}"

    if item_ids:
        item_ids_str = ", ".join(f"'{item_id}'" for item_id in item_ids)
        query += f"{where_prefix} id IN ({item_ids_str})"

    if sort_by_date:
        query += f"\nORDER BY item.created_at DESC"
    else:
        query += f"\nORDER BY RAND()"

    if n:
        query += f"\nLIMIT {n}"

    return query


def query_vector_ids(
    n: Optional[int] = None, index: Optional[int] = None, shuffle: bool = False
) -> str:
    query = f"""
SELECT DISTINCT point_id
FROM `{PROJECT_ID}.{VINTED_DATASET_ID}.{PINECONE_TABLE_ID}`
    """

    if shuffle and index is None:
        query += "\nORDER BY RAND()"

    if n:
        query += f"\nLIMIT {n}"

        if index:
            query += f"\nOFFSET {index * n}"

    return query


def query_interaction_items(
    n: Optional[int] = None, index: Optional[int] = None, shuffle: bool = False
) -> str:
    category_types_str = ", ".join([f"'{category_type}'" for category_type in CATEGORY_TYPES])
    
    query = f"""
WITH
Interactions AS (
SELECT DISTINCT item_id FROM `{PROJECT_ID}.{PROD_DATASET_ID}.{CLICK_OUT_TABLE_ID}`
UNION ALL
SELECT DISTINCT item_id FROM `{PROJECT_ID}.{PROD_DATASET_ID}.{SAVED_TABLE_ID}`)
, InteractionsWithCategory AS (
SELECT item_id, category_type
FROM Interactions
INNER JOIN `{PROJECT_ID}.{VINTED_DATASET_ID}.{ITEM_ACTIVE_TABLE_ID}` AS i ON Interactions.item_id = item.id)
, Data AS (
SELECT 
p.point_id, 
iwc.category_type, 
ROW_NUMBER() OVER (PARTITION BY p.point_id ORDER BY p.point_id) AS rn
FROM InteractionsWithCategory AS iwc
INNER JOIN `{PROJECT_ID}.{VINTED_DATASET_ID}.{PINECONE_TABLE_ID}` AS p USING (item_id)
WHERE iwc.category_type IN ({category_types_str}))   
SELECT point_id, category_type
FROM Data
WHERE rn = 1
    """

    if shuffle:
        query += "\nORDER BY RAND()"

    if n:
        query += f"\nLIMIT {n}"

        if index:
            query += f"\nOFFSET {index * n}"

    return query


def query_pinecone_points(item_ids: List[str]) -> str:
    item_ids_str = ", ".join([f"'{item_id}'" for item_id in item_ids])

    return f"""
SELECT point_id 
FROM `{PROJECT_ID}.{VINTED_DATASET_ID}.{PINECONE_TABLE_ID}` 
WHERE item_id IN ({item_ids_str})
    """


def query_points_to_delete(lookback_days: int) -> str:
    return f"""
SELECT DISTINCT p.point_id
FROM `{PROJECT_ID}.{VINTED_DATASET_ID}.{PINECONE_TABLE_ID}` AS p
INNER JOIN `{PROJECT_ID}.{VINTED_DATASET_ID}.{ITEM_ACTIVE_TABLE_ID}` AS i ON p.item_id = item.id
WHERE DATE(item.created_at) < DATE_SUB(CURRENT_DATE(), INTERVAL {lookback_days} DAY);
    """


def query_delete_points(lookback_days: int) -> bool:
    return f"""
CREATE OR REPLACE TABLE `{PROJECT_ID}.{VINTED_DATASET_ID}.{PINECONE_TABLE_ID}` AS
SELECT p.*
FROM `{PROJECT_ID}.{VINTED_DATASET_ID}.{PINECONE_TABLE_ID}` p
INNER JOIN `{PROJECT_ID}.{VINTED_DATASET_ID}.{ITEM_TABLE_ID}` i ON p.item_id = item.id
WHERE DATE(item.created_at) >= DATE_SUB(CURRENT_DATE(), INTERVAL {lookback_days} DAY)
    """


def query_delete_items(lookback_days: int) -> bool:
    return f"""
DELETE FROM `{PROJECT_ID}.{VINTED_DATASET_ID}.{ITEM_TABLE_ID}`
WHERE DATE(item.created_at) < DATE_SUB(CURRENT_DATE(), INTERVAL {lookback_days} DAY);
    """


def query_delete_sold(lookback_days: int) -> bool:
    return f"""
CREATE OR REPLACE TABLE `{PROJECT_ID}.{VINTED_DATASET_ID}.{SOLD_TABLE_ID}` AS
SELECT *
FROM `{PROJECT_ID}.{VINTED_DATASET_ID}.{SOLD_TABLE_ID}`
WHERE DATE(updated_at) >= DATE_SUB(CURRENT_DATE(), INTERVAL {lookback_days} DAY);
    """
