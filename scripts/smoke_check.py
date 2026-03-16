#!/usr/bin/env python
import argparse
import sys

import requests


def check(url: str, expected_status: int = 200) -> tuple[bool, str]:
    try:
        resp = requests.get(url, timeout=10)
        if resp.status_code != expected_status:
            return False, f"{url} -> {resp.status_code}"
        return True, f"{url} -> {resp.status_code}"
    except Exception as exc:
        return False, f"{url} -> ERROR: {exc}"


def main() -> int:
    parser = argparse.ArgumentParser(description="TGaggregator smoke check")
    parser.add_argument("--api", default="http://127.0.0.1:8000", help="API base URL")
    parser.add_argument("--ui", default="http://127.0.0.1:8501", help="UI URL")
    args = parser.parse_args()

    checks = [
        check(f"{args.api}/health"),
        check(f"{args.api}/status"),
        check(f"{args.api}/metrics"),
        check(f"{args.api}/channels"),
        check(f"{args.api}/feed?limit=1"),
        check(args.ui),
    ]

    ok = True
    for passed, message in checks:
        print(("OK   " if passed else "FAIL ") + message)
        ok = ok and passed

    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
