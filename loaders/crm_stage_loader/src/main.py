import argparse
import logging

from .loader import S_1, load_stage_changes


def main():
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

    parser = argparse.ArgumentParser(description="CRM stage changes loader")
    parser.add_argument(
        "--since",
        default=S_1.isoformat(),
        help="Date (inclusive) from which to load stage changes, in YYYY-MM-DD format. Default is 14 days ago.",
    )

    args = parser.parse_args()
    load_stage_changes(since=args.since)


if __name__ == "__main__":
    main()
