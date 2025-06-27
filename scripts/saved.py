import sys

sys.path.append("../")


import src


NUM_ITEMS = 1000
JOB_ID = "saved"
ASCENDING_ALPHA = 0.0
SECRETS_PATH = "../secrets.json"


def init_runner() -> src.runner.Runner:
    config = src.config.init_config(
        bq_client=bq_client,
        supabase_client=supabase_client,
        pinecone_index=pinecone_index,
        apify_client=apify_client,
        apify_actor_id=secrets.get("APIFY_ACTOR_ID"),
        from_saved=True,
        saved_ascending_alpha=ASCENDING_ALPHA,
    )

    return src.runner.Runner(config=config)


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


if __name__ == "__main__":
    secrets = src.utils.load_json(SECRETS_PATH)
    global bq_client, pinecone_index, apify_client, supabase_client

    (
        bq_client,
        pinecone_index,
        apify_client,
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

        n_sold_batch, success, status_codes_batch = runner.run(loader)

        n_sold += n_sold_batch
        n_success += int(success)
        n += 1
        runner.config.set_index(index + 1)

        src.bigquery.update_job_index(
            client=bq_client,
            job_id=runner.config.id,
            index=runner.config.index,
        )

        print(f"Batch #{n} | Sold: {n_sold} | Success rate: {n_success / n:.2f}")
