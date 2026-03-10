"""Dump all metadata from parquet files as pretty-printed JSON."""

import argparse
import json
import sys
from pathlib import Path

import pyarrow.parquet as pq

PANDAS_KEY = b"pandas"


def _decode_value(raw: bytes) -> str | dict | list:
    """Try to parse as JSON; fall back to plain string."""
    text = raw.decode()
    try:
        return json.loads(text)
    except (json.JSONDecodeError, ValueError):
        return text


def main() -> None:
    parser = argparse.ArgumentParser(description="Dump parquet file metadata as JSON.")
    parser.add_argument("files", nargs="+", metavar="parquet_file")
    parser.add_argument("--pandas", action="store_true", help="include pandas metadata")
    args = parser.parse_args()

    for p in args.files:
        path = Path(p)
        if not path.exists():
            print(f"{path}: NOT FOUND")
            continue
        try:
            schema = pq.read_schema(str(path))
        except Exception as e:
            print(f"{path}: ERROR reading schema — {e}")
            continue

        metadata = schema.metadata or {}
        result = {
            key.decode(): _decode_value(value)
            for key, value in sorted(metadata.items())
            if args.pandas or key != PANDAS_KEY
        }
        has_pandas = PANDAS_KEY in metadata
        print(f"{path}:")
        print(json.dumps(result, indent=2) if result else "  (no metadata)")
        if has_pandas and not args.pandas:
            print(
                "  (pandas metadata omitted; use --pandas to include)", file=sys.stderr
            )


if __name__ == "__main__":
    main()
