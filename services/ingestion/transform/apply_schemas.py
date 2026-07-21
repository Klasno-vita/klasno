from pathlib import Path
import argparse

from google.cloud import bigquery

SCHEMA_DIR = Path(__file__).parent / "schemas"
SCHEMA_FILES = [
    "control_table.sql",
    "metric_source_tables.sql",
    "sleep_sessions.sql",
    "stg_sleep_sessions.sql",
]


def apply_schemas(*, project_id: str, dataset: str, location: str) -> None:
    client = bigquery.Client(project=project_id, location=location)
    for filename in SCHEMA_FILES:
        sql = (SCHEMA_DIR / filename).read_text(encoding="utf-8").format(
            project_id=project_id,
            dataset=dataset,
        )
        client.query(sql).result()
        print(f"Applied {filename}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-id", required=True)
    parser.add_argument("--dataset", required=True)
    parser.add_argument("--location", default="asia-south1")
    args = parser.parse_args()

    apply_schemas(project_id=args.project_id, dataset=args.dataset, location=args.location)


if __name__ == "__main__":
    main()
