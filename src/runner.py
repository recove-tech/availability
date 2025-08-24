from typing import List, Tuple, Optional, Dict
from collections import defaultdict
from datetime import datetime
import asyncio, random

from google.cloud import bigquery

from src.models import Config, PineconeDataLoader
from src.bigquery import query_pinecone_points, run_query, insert_rows_json
from src.supabase import set_items_unavailable
from src.pinecone import delete_points_from_ids
from src.checker import BaseAvailabilityChecker, AsyncAvailabilityChecker


SUCCESS_RATE_THRESHOLD = 0.9


class Runner:
    def __init__(self, config: Config, checker: BaseAvailabilityChecker):
        self.config = config
        self.checker = checker

    def run(
        self,
        data_loader: PineconeDataLoader,
    ) -> Tuple[int, bool, float]:
        vinted_ids = data_loader.vinted_ids
        api_response = self.checker.run(vinted_ids)

        if not api_response:
            return 0, False, []

        n, n_success = 0, 0
        item_ids, point_ids, vinted_ids = defaultdict(list), defaultdict(list), []

        for entry, status in zip(data_loader, api_response):
            n += 1
            n_success += int(status.ok)

            if not status.is_available:
                item_ids[entry.category_type].append(entry.id)
                point_ids[entry.category_type].append(entry.point_id)
                vinted_ids.append(entry.vinted_id)

        updated = self._update(item_ids, vinted_ids, point_ids)
        n_sold = len(vinted_ids)
        success_rate = n_success / n if n > 0 else 0

        return n_sold, updated, success_rate

    async def run_async(
        self,
        data_loader: PineconeDataLoader,
        use_proxy: bool = False,
    ) -> Tuple[int, bool, float]:
        vinted_ids = data_loader.vinted_ids
        api_response = await self.checker.run(vinted_ids, use_proxy)

        if not api_response:
            return 0, False, 0.0

        n, n_success = 0, 0
        item_ids, point_ids, vinted_ids = defaultdict(list), defaultdict(list), []

        for entry, status in zip(data_loader, api_response):
            n += 1
            n_success += int(status.ok)

            if status.ok and not status.is_available:
                item_ids[entry.category_type].append(entry.id)
                point_ids[entry.category_type].append(entry.point_id)
                vinted_ids.append(entry.vinted_id)

        updated = self._update(item_ids, vinted_ids, point_ids)
        n_sold = len(vinted_ids)
        success_rate = n_success / n if n > 0 else 0

        return n_sold, updated, success_rate

    def _update(
        self,
        item_ids: Dict[str, List[str]],
        vinted_ids: List[str],
        point_ids: Dict[str, List[str]],
    ) -> Optional[bool]:
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
