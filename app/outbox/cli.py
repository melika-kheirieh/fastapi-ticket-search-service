import argparse

from app.db.session import SessionLocal
from app.outbox.processor import OutboxProcessor


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Process outbox events and sync them to Elasticsearch."
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=20,
        help="Maximum number of outbox events to process.",
    )
    parser.add_argument(
        "--max-retry-count",
        type=int,
        default=3,
        help="Maximum retry count for failed outbox events.",
    )

    args = parser.parse_args()

    db = SessionLocal()
    try:
        processor = OutboxProcessor(db)
        result = processor.process_pending_events(
            limit=args.limit,
            max_retry_count=args.max_retry_count,
        )

        print(
            "Outbox processing finished: "
            f"processed={result.processed}, "
            f"failed={result.failed}, "
            f"skipped={result.skipped}"
        )
    finally:
        db.close()


if __name__ == "__main__":
    main()