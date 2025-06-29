import sys

sys.path.append("../")

from typing import List
import tqdm

import src


NUM_ITEMS = 1000
NUM_NEIGHBORS = 50
SECRETS_PATH = "../secrets.json"


def init_runner() -> src.runner.Runner:
    secrets = src.utils.load_json(SECRETS_PATH)

    proxy_config = src.models.ProxyConfig(
        password=secrets.get("APIFY_PROXY_PASSWORD"),
    )

    checker = src.checker.AsyncAvailabilityChecker(
        proxy_config=proxy_config,
    )

    bq_client, pinecone_index, _ = src.config.init_clients(
        secrets=secrets,
    )

    config = src.config.init_config(
        bq_client=bq_client,
        pinecone_index=pinecone_index,
        from_interactions=True,
    )

    return src.runner.Runner(config=config, checker=checker)


def load_data(runner: src.runner.Runner) -> List[str]:
    query = src.bigquery.query_interaction_items(
        n=NUM_ITEMS,
        shuffle=True,
    )

    loader = src.bigquery.run_query(
        client=runner.config.bq_client, query=query, to_list=False
    )

    point_ids, namespaces = [], []

    for row in loader:
        point_ids.append(row.point_id)
        namespaces.append(row.category_type)

    return point_ids, namespaces


async def main():
    runner = init_runner()
    print(f"Config: {runner.config}")

    n, n_sold, n_success = 0, 0, 0
    point_ids, namespaces = load_data(runner)
    loop = tqdm.tqdm(iterable=zip(point_ids, namespaces), total=len(point_ids))

    for point_id, namespace in loop:
        if namespace is None:
            continue

        loader = src.pinecone.get_neighbors(
            index=runner.config.pinecone_index,
            namespace=namespace,
            point_id=point_id,
            n=NUM_NEIGHBORS,
        )

        try:
            n_sold_batch, success = await runner.run_async(loader)
        except Exception as e:
            n_sold_batch, success = 0, False

        n_sold += n_sold_batch
        n_success += int(success)
        n += 1

        print(
            f"Batch #{n} | "
            f"Success: {success} | "
            f"Sold: {n_sold} | "
            f"Success rate: {n_success / n:.2f}"
        )


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
