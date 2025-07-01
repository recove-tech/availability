import sys

sys.path.append("../")

import logging
from datetime import datetime
from google.cloud import bigquery
import src


NUM_ITEMS = 100000
RUN_EVERY = 50
IS_WOMEN_ALPHA = 1.0
SORT_BY_DATE_ALPHA = 0.2
USE_PROXY_ALPHA = 1.0

SECRETS_PATH = "../secrets.json"
LOG_DIR = "../logs"


def setup_logging():
    today = datetime.now().strftime("%Y%m%d")
    log_file = f"{LOG_DIR}/all_{today}.log"

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=[logging.FileHandler(log_file), logging.StreamHandler()],
    )


def init_runner() -> src.runner.Runner:
    secrets = src.utils.load_json(SECRETS_PATH)

    # replace with random.choice
    apify_proxy_password = secrets.get("APIFY_PROXY_PASSWORD")[1]

    proxy_config = src.models.ProxyConfig(
        password=apify_proxy_password,
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
        is_women_alpha=IS_WOMEN_ALPHA,
        sort_by_date_alpha=SORT_BY_DATE_ALPHA,
    )

    return src.runner.Runner(config=config, checker=checker)


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


async def main():
    setup_logging()

    runner = init_runner()
    logging.info(f"Config: {runner.config}")

    iterator = load_from_bigquery(runner)
    loader = src.models.PineconeDataLoader()

    use_proxy = False
    n, n_sold, success_rate_list = 0, 0, []

    for row in iterator:
        entry = src.models.PineconeEntry.from_dict(dict(row))
        loader.add(entry)

        if loader.total_rows % RUN_EVERY == 0:
            n += 1
            use_proxy = src.utils.use_proxy_func(use_proxy, USE_PROXY_ALPHA)

            n_sold_batch, updated, success_rate = await runner.run_async(
                loader, use_proxy
            )

            success_rate_list.append(success_rate)
            average_success_rate = sum(success_rate_list) / len(success_rate_list)
            n_sold += n_sold_batch

            loader = src.models.PineconeDataLoader()

            logging.info(
                f"Batch #{n} | "
                f"Proxy: {use_proxy} | "
                f"Updated: {updated} | "
                f"Sold: {n_sold_batch} | "
                f"Total sold: {n_sold} | "
                f"Success rate: {success_rate:.2f} | "
                f"Average success rate: {average_success_rate:.2f}"
            )


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
