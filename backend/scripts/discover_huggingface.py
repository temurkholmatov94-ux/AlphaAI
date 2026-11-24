import argparse

from app.database import SessionLocal
from app.discovery.huggingface import HuggingFaceDiscovery


def main() -> None:
    parser = argparse.ArgumentParser(description="Discover Hugging Face models into the AlphaAI review queue.")
    parser.add_argument("--limit", type=int, default=50)
    parser.add_argument("--search", type=str, default=None)
    parser.add_argument("--pipeline-tag", type=str, default=None)
    args = parser.parse_args()

    db = SessionLocal()
    try:
        result = HuggingFaceDiscovery().ingest(
            db,
            limit=args.limit,
            search=args.search,
            pipeline_tag=args.pipeline_tag,
        )
        print(
            "Discovery complete: "
            f"fetched={result['fetched']} created={result['created']} updated={result['updated']}"
        )
        print("New records remain review-required and are not exposed by the public catalog.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
