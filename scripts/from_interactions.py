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

    bq_client, pinecone_index, apify_client, _ = src.config.init_clients(
        secrets=secrets,
    )

    config = src.config.init_config(
        bq_client=bq_client,
        pinecone_index=pinecone_index,
        apify_client=apify_client,
        apify_actor_id=secrets.get("APIFY_ACTOR_ID"),
        from_interactions=True,
    )

    return src.runner.Runner(config=config)


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


def main():
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

        n_sold_batch, success, status_codes_batch = runner.run(loader)

        n_sold += n_sold_batch
        n_success += int(success)
        n += 1

        print(f"Batch #{n} | Sold: {n_sold} | Success rate: {n_success / n:.2f}")


if __name__ == "__main__":
    main()
