#!/usr/bin/env python3
"""Verify API rate limiting is working against a running smplFrm instance.

Usage:
    python scripts/verify_rate_limits.py [--host HOST] [--port PORT]

Defaults to http://localhost:8321. Requires the server to be running.
Uses the reusable tester classes from scripts/utils/rate_limit_tester.py.
"""

import argparse
import sys
import time

import requests

from utils.rate_limit_tester import (
    AnonThrottleTester,
    AuthThrottleTester,
    TaskThrottleTester,
    RecoveryTester,
)


def main():
    parser = argparse.ArgumentParser(
        description="Verify API rate limits on a running smplFrm instance"
    )
    parser.add_argument(
        "--host", default="localhost", help="Server hostname (default: localhost)"
    )
    parser.add_argument(
        "--port", type=int, default=8321, help="Server port (default: 8321)"
    )
    parser.add_argument(
        "--anon-limit",
        type=int,
        default=500,
        help="Expected anonymous rate limit (default: 500)",
    )
    parser.add_argument(
        "--task-limit",
        type=int,
        default=10,
        help="Expected task rate limit (default: 10)",
    )
    parser.add_argument(
        "--test-recovery",
        action="store_true",
        help="Include the recovery test (waits 65s+)",
    )
    args = parser.parse_args()

    base_url = f"http://{args.host}:{args.port}"

    print(f"Verifying rate limits against {base_url}")
    print(f"Expected limits: anon={args.anon_limit}/min, task={args.task_limit}/min")

    # Quick connectivity check
    try:
        resp = requests.get(f"{base_url}/api/v1/configs", timeout=5)
        print(f"Server reachable (HTTP {resp.status_code})\n")
    except requests.ConnectionError:
        print(f"ERROR: Cannot connect to {base_url}. Is the server running?")
        sys.exit(1)

    results = []

    # Task endpoint test first (lower limit, faster to verify)
    print("=" * 60)
    print("Running: Task Endpoint Throttle")
    print("=" * 60)
    task_tester = TaskThrottleTester(base_url=base_url, limit=args.task_limit)
    task_result = task_tester.run()
    task_result.print_report()
    results.append(task_result)

    # Wait to avoid cross-test interference
    print("\n  Waiting 5s before next test...")
    time.sleep(5)

    # Anonymous throttle test
    print("\n" + "=" * 60)
    print("Running: Anonymous Global Throttle")
    print("=" * 60)
    anon_tester = AnonThrottleTester(base_url=base_url, limit=args.anon_limit)
    anon_result = anon_tester.run()
    anon_result.print_report()
    results.append(anon_result)

    # Recovery test (optional, takes 65s+)
    if args.test_recovery:
        print("\n  Waiting 5s before recovery test...")
        time.sleep(5)
        print("\n" + "=" * 60)
        print("Running: Rate Window Recovery")
        print("=" * 60)
        recovery_tester = RecoveryTester(base_url=base_url)
        recovery_result = recovery_tester.run()
        recovery_result.print_report()
        results.append(recovery_result)

    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    passed = sum(1 for r in results if r.passed)
    failed = sum(1 for r in results if not r.passed)

    for r in results:
        status = "PASS" if r.passed else "FAIL"
        print(f"  [{status}] {r.name} — {r.actual_successes} requests before throttle")

    print(f"\n  {passed} passed, {failed} failed")

    if failed > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
