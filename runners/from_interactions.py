import sys

sys.path.append("/app")

from typing import List
import json, os, tqdm

import src


NUM_ITEMS = 1000
NUM_NEIGHBORS = 50
RUNNER_MODE = "driver"


def init_runner() -> src.runner.Runner:
    secrets = json.loads(os.getenv("SECRETS_JSON"))

    bq_client, pinecone_index, vinted_client, driver, _ = src.config.init_clients(
        secrets=secrets,
        mode=RUNNER_MODE,
    )

    config = src.config.init_config(
        bq_client=bq_client,
        pinecone_index=pinecone_index,
        vinted_client=vinted_client,
        driver=driver,
        from_interactions=True,
    )

    return src.runner.Runner(
        mode=RUNNER_MODE,
        config=config,
    )


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

    point_ids, namespaces = load_data(runner)
    loop = tqdm.tqdm(iterable=zip(point_ids, namespaces), total=len(point_ids))

    for point_id, namespace in loop:
        if namespace is None:
            continue

        data_loader = src.pinecone.get_neighbors(
            index=runner.config.pinecone_index,
            namespace=namespace,
            point_id=point_id,
            n=NUM_NEIGHBORS,
        )

        runner.run(data_loader, loop)


if __name__ == "__main__":
    main()
