from typing import List, Tuple, Optional, Dict
from collections import defaultdict
from datetime import datetime

from google.cloud import bigquery

from src.models import Config, PineconeDataLoader
from src.actor import get_actor_response
from src.bigquery import query_pinecone_points, run_query, insert_rows_json
from src.supabase import set_items_unavailable
from src.pinecone import delete_points_from_ids


SUCCESS_RATE_THRESHOLD = 0.9


class Runner:
    def __init__(self, config: Config):
        self.config = config

    def run(
        self,
        data_loader: PineconeDataLoader,
    ) -> Tuple[int, bool, List[int]]:
        status_codes = []
        vinted_ids = data_loader.vinted_ids

        apify_response = get_actor_response(
            client=self.config.apify_client,
            actor_id=self.config.apify_actor_id,
            item_ids=vinted_ids,
        )

        if not apify_response:
            return 0, False, []

        item_ids, point_ids, vinted_ids = defaultdict(list), defaultdict(list), []

        for entry, response in zip(data_loader, apify_response):
            is_available = response.get("is_available")
            status_codes.append(response.get("status_code"))

            if not is_available:
                item_ids[entry.category_type].append(entry.id)
                point_ids[entry.category_type].append(entry.point_id)
                vinted_ids.append(entry.vinted_id)

        success = self._update(item_ids, vinted_ids, point_ids)
        n_sold = len(vinted_ids)

        return n_sold, success, status_codes

    def _update(
        self,
        item_ids: Dict[str, List[str]],
        vinted_ids: List[str],
        point_ids: Dict[str, List[str]],
    ) -> Optional[bool]:
        current_time = datetime.now().isoformat()
        success_rate = 0.0

        for namespace, namespace_point_ids in point_ids.items():
            namespace_item_ids = item_ids.get(namespace, [])

            if len(namespace_point_ids) == 0:
                pinecone_points_query = query_pinecone_points(
                    item_ids=namespace_item_ids
                )

                loader = run_query(
                    self.config.bq_client, pinecone_points_query, to_list=False
                )

                if loader.total_rows == 0:
                    return False

                namespace_point_ids = [row.point_id for row in loader]

            if self.config.supabase_client:
                success = set_items_unavailable(
                    client=self.config.supabase_client,
                    item_ids=namespace_item_ids,
                )

            success_rate, failed = delete_points_from_ids(
                index=self.config.pinecone_index,
                ids=namespace_point_ids,
                namespace=namespace,
                verbose=False,
            )

        if success_rate > SUCCESS_RATE_THRESHOLD:
            return insert_rows_json(
                client=self.config.bq_client,
                vinted_ids=vinted_ids,
            )

        return False
