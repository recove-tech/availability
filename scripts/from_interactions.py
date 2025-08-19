import sys

sys.path.append("../")

import logging
from datetime import datetime
from typing import List, Tuple

import src


config_dict = src.utils.load_yaml("config.yaml")

script_config = src.models.ScriptConfig.from_config_dict(
    config_dict=config_dict,
    config_key="FROM_INTERACTIONS",
)


def setup_logging():
    today = datetime.now().strftime("%Y%m%d")
    log_file = f"{script_config.log_dir}/from_interactions_{today}.log"

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=[logging.FileHandler(log_file), logging.StreamHandler()],
    )


def init_runner() -> src.runner.Runner:
    secrets = src.utils.load_json(script_config.secrets_path)

    webshare_config = src.models.WebshareProxyConfig.from_list(
        proxies=secrets["WEBSHARE_PROXIES"],
    )

    proxy_config = src.models.ProxyConfig.from_webshare(
        proxy=webshare_config,
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
        sort_by_date_alpha=script_config.sort_by_date_alpha,
        days_lookback=script_config.days_lookback,
    )

    return src.runner.Runner(config=config, checker=checker)


def load_data(runner: src.runner.Runner) -> Tuple[List[str], List[str]]:
    query = src.bigquery.query_interaction_items(
        n=script_config.num_items,
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
    setup_logging()

    runner = init_runner()
    logging.info(f"Config: {runner.config}")

    use_proxy = False
    n, n_sold, success_rate_list = 0, 0, []
    point_ids, namespaces = load_data(runner)

    for point_id, namespace in zip(point_ids, namespaces):
        if namespace is None:
            continue

        loader = src.pinecone.get_neighbors(
            index=runner.config.pinecone_index,
            namespace=namespace,
            point_id=point_id,
            n=script_config.num_neighbors,
            days_lookback=runner.config.days_lookback,
        )

        try:
            use_proxy = src.utils.use_proxy_func(
                use_proxy, script_config.use_proxy_alpha
            )

            n_sold_batch, updated, success_rate = await runner.run_async(
                loader, use_proxy
            )

        except Exception as e:
            n_sold_batch, updated, success_rate = 0, False, 0
            logging.error(f"Error in batch: {str(e)}")

        n_sold += n_sold_batch
        success_rate_list.append(success_rate)
        average_success_rate = sum(success_rate_list) / len(success_rate_list)
        n += 1

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
