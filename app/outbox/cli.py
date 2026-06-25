import argparse

from app.db.session import SessionLocal
from app.outbox.processor import OutboxProcessor


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Process pending outbox events and sync them to Elasticsearch."
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=20,
        help="Maximum number of pending outbox events to process.",
    )

    args = parser.parse_args()

    db = SessionLocal()
    try:
        processor = OutboxProcessor(db)
        result = processor.process_pending_events(limit=args.limit)

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