from typing import Literal, List

PROJECT_ID = "recove-450509"
VINTED_DATASET_ID = "vinted"
PROD_DATASET_ID = "prod"

ITEM_TABLE_ID = "item"
ITEM_ACTIVE_TABLE_ID = "item_active"
INDEX_TABLE_ID = "item_active_index"
SOLD_TABLE_ID = "sold"
PINECONE_TABLE_ID = "pinecone"
CLICK_OUT_TABLE_ID = "click_out"
SAVED_TABLE_ID = "saved"
VIEWED_ITEMS_TABLE_ID = "items"
CATALOG_TABLE_ID = "catalog_importance"

SUPABASE_SAVED_TABLE_ID = "saved_item"

VINTED_ID_FIELD = "vinted_id"
AVAILABLE_FIELD = "is_available"

PINECONE_INDEX_NAME = "vinted"

MAX_RETRIES = 3
INITIAL_SLEEP_TIME = 10
MAX_SLEEP_TIME = 60
RATE_LIMIT_SLEEP_TIME = 30

CatalogScore = Literal[1, 2, 3]
CATALOG_SCORE_VALUES: List[CatalogScore] = [1, 2, 3]
CATEGORY_TYPES: List[str] = [
    "outerwear",
    "top",
    "bottom",
    "dress",
    "accessories",
    "footwear",
]
