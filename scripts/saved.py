import sys

sys.path.append("../")


import src


NUM_ITEMS = 1000
JOB_ID = "saved"
ASCENDING_ALPHA = 0.0
SECRETS_PATH = "../secrets.json"


def init_runner() -> src.runner.Runner:
    secrets = src.utils.load_json(SECRETS_PATH)

    proxy_config = src.models.ProxyConfig(
        password=secrets.get("APIFY_PROXY_PASSWORD"),
    )

    checker = src.checker.AsyncAvailabilityChecker(
        proxy_config=proxy_config,
    )

    config = src.config.init_config(
        bq_client=bq_client,
        supabase_client=supabase_client,
        pinecone_index=pinecone_index,
        from_saved=True,
        saved_ascending_alpha=ASCENDING_ALPHA,
    )

    return src.runner.Runner(config=config, checker=checker)


def get_loader(runner: src.runner.Runner) -> src.models.PineconeDataLoader:
    entries = src.supabase.get_saved_items(
        client=runner.config.supabase_client,
        n=NUM_ITEMS,
        index=runner.config.index,
        ascending=runner.config.ascending_saved,
    )

    if len(entries) == 0:
        runner.config.index = 0

        entries = src.supabase.get_saved_items(
            client=runner.config.supabase_client,
            n=NUM_ITEMS,
            index=runner.config.index,
        )

    return src.models.PineconeDataLoader(entries)


async def main():
    secrets = src.utils.load_json(SECRETS_PATH)
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
    n, n_sold, n_success = 0, 0, 0

    while True:
        print(f"Config: {runner.config.id} | Index: {runner.config.index}")

        loader = get_loader(runner)

        if len(loader.entries) == 0:
            raise Exception("No entries found")

        try:
            n_sold_batch, success = await runner.run_async(loader)
        except Exception as e:
            n_sold_batch, success = 0, False

        n_sold += n_sold_batch
        n_success += int(success)
        n += 1

        runner.config.set_index(index + 1)

        src.bigquery.update_job_index(
            client=bq_client,
            job_id=runner.config.id,
            index=runner.config.index,
        )

        print(
            f"Batch #{n} | "
            f"Success: {success} | "
            f"Sold: {n_sold} | "
            f"Success rate: {n_success / n:.2f}"
        )


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
