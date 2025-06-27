import sys

sys.path.append("../")

from typing import List, Dict
from google.cloud import bigquery

import src


NUM_ITEMS = 100000
RUN_EVERY = 500
IS_WOMEN_ALPHA = 1.0
SORT_BY_DATE_ALPHA = 0.2
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
        is_women_alpha=IS_WOMEN_ALPHA,
        sort_by_date_alpha=SORT_BY_DATE_ALPHA,
    )

    return src.runner.Runner(config=config)


def load_from_bigquery(
    runner: src.runner.Runner,
) -> bigquery.table.RowIterator:
    query_kwargs = {
        "n": NUM_ITEMS,
        "is_women": runner.config.is_women,
        "sort_by_date": runner.config.sort_by_date,
    }

    query = src.bigquery.query_items(**query_kwargs)

    return src.bigquery.run_query(
        client=runner.config.bq_client, query=query, to_list=False
    )


def main():
    runner = init_runner()
    print(f"Config: {runner.config}")

    iterator = load_from_bigquery(runner)

    status_codes = []
    n, n_sold, n_success = 0, 0, 0
    loader = src.models.PineconeDataLoader()

    for row in iterator:
        entry = src.models.PineconeEntry.from_dict(dict(row))
        loader.add(entry)

        if loader.total_rows % RUN_EVERY == 0:
            n_sold_batch, success, status_codes_batch = runner.run(loader)

            status_codes.extend(status_codes_batch)
            n_sold += n_sold_batch
            n_success += int(success)
            n += 1

            print(
                f"Batch #{n} | Sold: {n_sold_total} | Success rate: {n_success / n:.2f}"
            )

            src.utils.display_status_code_stats(status_codes)

            print("-" * 100)


if __name__ == "__main__":
    main()
