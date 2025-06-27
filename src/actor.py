from typing import List, Dict

from apify_client import ApifyClient


def get_actor_response(
    client: ApifyClient, actor_id: str, item_ids: List[int]
) -> List[Dict]:
    run_input = {"urls": [{"url": generate_api_url(item_id)} for item_id in item_ids]}

    run = client.actor(actor_id).call(run_input=run_input)
    response = client.dataset(run["defaultDatasetId"]).list_items().items

    return response[0].get("data", [])


def generate_api_url(item_id: int) -> str:
    return f"https://www.vinted.fr/api/v2/items/{item_id}/details"
