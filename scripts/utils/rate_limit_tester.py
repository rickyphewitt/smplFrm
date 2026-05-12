"""Rate limit testing utilities for verifying throttle behavior.

Provides reusable classes for hammering API endpoints and reporting
whether rate limits are correctly enforced.

Usage:
    from scripts.utils.rate_limit_tester import (
        AnonThrottleTester,
        AuthThrottleTester,
        TaskThrottleTester,
    )

    tester = AnonThrottleTester(base_url="http://localhost:8321")
    result = tester.run()
    result.print_report()
"""

import time
from dataclasses import dataclass, field

import requests


@dataclass
class ThrottleTestResult:
    """Result of a throttle test run."""

    name: str
    endpoint: str
    expected_limit: int
    actual_successes: int
    was_throttled: bool
    retry_after: int | None = None
    response_detail: str | None = None
    content_type_ok: bool = False
    issues: list[str] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        """Test passes if throttled and no response format issues."""
        return self.was_throttled and len(self.issues) == 0

    def print_report(self):
        """Print a human-readable report of this test result."""
        status = "PASS" if self.passed else "FAIL"
        print(f"\n[{status}] {self.name}")
        print(f"  Endpoint: {self.endpoint}")
        print(f"  Expected limit: {self.expected_limit}/min")
        print(f"  Actual successes before throttle: {self.actual_successes}")
        print(f"  Was throttled: {self.was_throttled}")
        if self.retry_after is not None:
            print(f"  Retry-After: {self.retry_after}s")
        if self.response_detail:
            print(f"  Detail: {self.response_detail}")
        if self.issues:
            print(f"  Issues:")
            for issue in self.issues:
                print(f"    - {issue}")


class BaseThrottleTester:
    """Base class for throttle testing.

    Subclasses define the endpoint, expected limit, and how to build requests.
    """

    name: str = "Base Throttle Test"
    endpoint_path: str = "/api/v1/configs"
    default_limit: int = 60

    def __init__(
        self, base_url: str = "http://localhost:8321", limit: int | None = None
    ):
        self.base_url = base_url.rstrip("/")
        self.limit = limit or self.default_limit
        self.session = requests.Session()

    @property
    def url(self) -> str:
        return f"{self.base_url}{self.endpoint_path}"

    def setup_session(self):
        """Override to configure auth headers or other session setup."""
        pass

    def make_request(self) -> requests.Response:
        """Make a single request. Override for POST or custom methods."""
        return self.session.get(self.url, timeout=10)

    def validate_429(self, response: requests.Response) -> list[str]:
        """Check that a 429 response has correct format."""
        issues = []

        # Retry-After header
        if "Retry-After" not in response.headers:
            issues.append("Missing Retry-After header")
        else:
            try:
                val = int(response.headers["Retry-After"])
                if val < 1:
                    issues.append(f"Retry-After not positive: {val}")
            except ValueError:
                issues.append(
                    f"Retry-After not an integer: {response.headers['Retry-After']}"
                )

        # Content-Type
        content_type = response.headers.get("Content-Type", "")
        if "application/json" not in content_type:
            issues.append(f"Content-Type not JSON: {content_type}")

        # Body
        try:
            body = response.json()
            if "detail" not in body:
                issues.append("Response body missing 'detail' field")
        except Exception:
            issues.append("Response body is not valid JSON")

        return issues

    def run(self, overshoot: int = 5) -> ThrottleTestResult:
        """Send requests until throttled or limit+overshoot reached.

        Args:
            overshoot: Extra requests beyond the expected limit to send.

        Returns:
            ThrottleTestResult with all findings.
        """
        self.setup_session()
        total = self.limit + overshoot
        successes = 0
        throttled_response = None

        for i in range(total):
            try:
                resp = self.make_request()
            except requests.RequestException as e:
                return ThrottleTestResult(
                    name=self.name,
                    endpoint=self.url,
                    expected_limit=self.limit,
                    actual_successes=successes,
                    was_throttled=False,
                    issues=[f"Connection error on request #{i + 1}: {e}"],
                )

            if resp.status_code == 200:
                successes += 1
            elif resp.status_code == 429:
                throttled_response = resp
                break
            else:
                # Unexpected status — keep going but note it
                pass

        if throttled_response is None:
            return ThrottleTestResult(
                name=self.name,
                endpoint=self.url,
                expected_limit=self.limit,
                actual_successes=successes,
                was_throttled=False,
                issues=[f"Sent {total} requests without being throttled"],
            )

        issues = self.validate_429(throttled_response)
        retry_after = None
        detail = None
        content_type_ok = "application/json" in throttled_response.headers.get(
            "Content-Type", ""
        )

        try:
            retry_after = int(throttled_response.headers.get("Retry-After", "0"))
        except ValueError:
            pass

        try:
            detail = throttled_response.json().get("detail")
        except Exception:
            pass

        return ThrottleTestResult(
            name=self.name,
            endpoint=self.url,
            expected_limit=self.limit,
            actual_successes=successes,
            was_throttled=True,
            retry_after=retry_after,
            response_detail=detail,
            content_type_ok=content_type_ok,
            issues=issues,
        )


class AnonThrottleTester(BaseThrottleTester):
    """Tests the anonymous global rate limit against a general endpoint."""

    name = "Anonymous Global Throttle"
    endpoint_path = "/api/v1/configs"
    default_limit = 60


class AuthThrottleTester(BaseThrottleTester):
    """Tests the authenticated global rate limit.

    Requires credentials to be provided for session setup.
    """

    name = "Authenticated Global Throttle"
    endpoint_path = "/api/v1/configs"
    default_limit = 120

    def __init__(
        self,
        base_url: str = "http://localhost:8321",
        limit: int | None = None,
        username: str = "",
        password: str = "",
        token: str = "",
    ):
        super().__init__(base_url, limit)
        self.username = username
        self.password = password
        self.token = token

    def setup_session(self):
        """Configure session with auth credentials."""
        if self.token:
            self.session.headers["Authorization"] = f"Token {self.token}"
        elif self.username and self.password:
            self.session.auth = (self.username, self.password)


class TaskThrottleTester(BaseThrottleTester):
    """Tests the task endpoint's stricter rate limit."""

    name = "Task Endpoint Throttle"
    endpoint_path = "/api/v1/tasks"
    default_limit = 10


class RecoveryTester:
    """Tests that rate limits recover after the window elapses.

    WARNING: This test takes at least `wait_seconds` to complete.
    """

    def __init__(
        self,
        base_url: str = "http://localhost:8321",
        wait_seconds: int = 65,
    ):
        self.base_url = base_url.rstrip("/")
        self.wait_seconds = wait_seconds

    def run(self) -> ThrottleTestResult:
        """Exhaust the limit, wait, then verify recovery."""
        # First exhaust the anonymous limit using a low-limit tester
        tester = TaskThrottleTester(base_url=self.base_url)
        exhaust_result = tester.run()

        if not exhaust_result.was_throttled:
            return ThrottleTestResult(
                name="Rate Window Recovery",
                endpoint=tester.url,
                expected_limit=tester.limit,
                actual_successes=0,
                was_throttled=False,
                issues=["Could not exhaust rate limit to test recovery"],
            )

        print(
            f"  Rate limit exhausted. Waiting {self.wait_seconds}s for window reset..."
        )
        time.sleep(self.wait_seconds)

        # Try again — should succeed
        try:
            resp = requests.get(tester.url, timeout=10)
        except requests.RequestException as e:
            return ThrottleTestResult(
                name="Rate Window Recovery",
                endpoint=tester.url,
                expected_limit=tester.limit,
                actual_successes=0,
                was_throttled=True,
                issues=[f"Connection error after wait: {e}"],
            )

        recovered = resp.status_code == 200
        issues = (
            []
            if recovered
            else [
                f"Still throttled after {self.wait_seconds}s wait (HTTP {resp.status_code})"
            ]
        )

        return ThrottleTestResult(
            name="Rate Window Recovery",
            endpoint=tester.url,
            expected_limit=tester.limit,
            actual_successes=1 if recovered else 0,
            was_throttled=not recovered,
            issues=issues,
        )
