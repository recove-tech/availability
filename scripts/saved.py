import sys

sys.path.append("../")

import src


config = src.utils.load_yaml("config.yaml")

config_dict = src.utils.load_yaml("config.yaml")

script_config = src.models.ScriptConfig.from_config_dict(
    config_dict=config_dict,
    config_key="SAVED",
)


def init_runner() -> src.runner.Runner:
    secrets = src.utils.load_json(script_config.secrets_path)

    apify_proxy_password = secrets.get("APIFY_PROXY_PASSWORD")[-1]

    proxy_config = src.models.ProxyConfig(
        password=apify_proxy_password,
    )

    checker = src.checker.AsyncAvailabilityChecker(
        proxy_config=proxy_config,
    )

    config = src.config.init_config(
        bq_client=bq_client,
        supabase_client=supabase_client,
        pinecone_index=pinecone_index,
        from_saved=True,
    )

    return src.runner.Runner(config=config, checker=checker)


def get_loader(runner: src.runner.Runner) -> src.models.PineconeDataLoader:
    entries = src.supabase.get_saved_items(
        client=runner.config.supabase_client,
        n=1000,
        index=runner.config.index,
        ascending=runner.config.ascending_saved,
    )

    if len(entries) == 0:
        runner.config.index = 0

        entries = src.supabase.get_saved_items(
            client=runner.config.supabase_client,
            n=1000,
            index=runner.config.index,
        )

    return src.models.PineconeDataLoader(entries)


async def main():
    secrets = src.utils.load_json(script_config.secrets_path)
    global bq_client, pinecone_index, supabase_client

    (
        bq_client,
        pinecone_index,
        supabase_client,
    ) = src.config.init_clients(
        secrets=secrets,
        with_supabase=True,
    )

    runner = init_runner()
    index = runner.config.index

    use_proxy = False
    n, n_sold, success_rate_list = 0, 0, []

    while True:
        print(f"Config: {runner.config}")

        loader = get_loader(runner)

        if len(loader.entries) == 0:
            raise Exception("No entries found")

        try:
            n_sold_batch, updated, success_rate = await runner.run_async(
                loader, use_proxy=True
            )

        except Exception as e:
            n_sold_batch, updated, success_rate = 0, False, 0

        n_sold += n_sold_batch
        n += 1
        success_rate_list.append(success_rate)
        average_success_rate = sum(success_rate_list) / len(success_rate_list)

        runner.config.set_index(index + 1)

        src.bigquery.update_job_index(
            client=bq_client,
            job_id=runner.config.id,
            index=runner.config.index,
        )

        print(
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
