from __future__ import annotations

import argparse
import json
import sys
from typing import Any

from loadweave.config import ConfigError, load_config, load_dotenv
from loadweave.pipeline import Pipeline
from loadweave.registry import SINKS, SOURCES, TRANSFORMS, build_sink, build_source, build_transform


def create_pipeline(config: dict[str, Any]) -> Pipeline:
    return Pipeline(
        build_source(config["source"]),
        [build_transform(spec) for spec in config.get("transforms", [])],
        build_sink(config["sink"]),
    )


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(prog="loadweave", description="Composable streaming ETL")
    commands = root.add_subparsers(dest="command", required=True)
    for name in ("run", "check"):
        command = commands.add_parser(name)
        command.add_argument("config")
    commands.add_parser("components")
    return root


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    try:
        if args.command == "components":
            print("sources: " + ", ".join(sorted(SOURCES)))
            print("transforms: " + ", ".join(sorted(TRANSFORMS)))
            print("sinks: " + ", ".join(sorted(SINKS)))
            return 0
        load_dotenv()
        pipeline = create_pipeline(load_config(args.config))
        if args.command == "check":
            print(f"valid: {args.config}")
            return 0
        result = pipeline.run()
        print(json.dumps(result.__dict__, separators=(",", ":")))
        return 0
    except (ConfigError, OSError, TypeError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
