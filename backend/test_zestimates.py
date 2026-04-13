"""
Zillow Estimate Agent -- Integration Tests
==========================================
Validates that the /chat endpoint returns correct Zestimates for known addresses.

Usage:
    python test_zestimates.py            # Run all tests
    python test_zestimates.py --verbose  # Run with detailed output
"""

import json
import sys
import requests

API_URL = "http://localhost:8000/chat"
TIMEOUT = 60  # seconds -- LLM + BridgeData can be slow

# -- Test Cases ----------------------------------------------------------------
# tolerance_percent accounts for minor Zestimate fluctuations over time.
TEST_CASES = [
    {
        "query": "What is the Zestimate for 328 26th Avenue, Seattle, WA 98122?",
        "expected_zestimate": 1_158_800,
        "address_hint": "328 26th Avenue, Seattle, WA 98122",
    },
    {
        "query": "What is the Zestimate for 14505 Simonds Road NE #C, Kirkland, WA 98034?",
        "expected_zestimate": 754_400,
        "address_hint": "14505 Simonds Road NE #C, Kirkland, WA 98034",
    },
    {
        "query": "What is the Zestimate for 1430 Bar Harbor Cir, Dallas, TX 75232?",
        "expected_zestimate": 730_400,
        "address_hint": "1430 Bar Harbor Cir, Dallas, TX 75232",
    },
    {
        "query": "What is the Zestimate for 53 Fairview Avenue, Kingston, NY 12401?",
        "expected_zestimate": 399_000,
        "address_hint": "53 Fairview Avenue, Kingston, NY 12401",
    },
    {
        "query": "What is the Zestimate for 3838 Winthrope Cir, Virginia Beach, VA 23452?",
        "expected_zestimate": 752_500,
        "address_hint": "3838 Winthrope Cir, Virginia Beach, VA 23452",
    },
]

TOLERANCE_PERCENT = 5  # allow +/-5% drift in Zestimate values


# -- Helpers -------------------------------------------------------------------
def fmt_price(val):
    return f"${val:,.0f}" if val else "N/A"


def within_tolerance(actual, expected, pct):
    lower = expected * (1 - pct / 100)
    upper = expected * (1 + pct / 100)
    return lower <= actual <= upper


# -- Runner --------------------------------------------------------------------
def run_tests(verbose=False):
    passed = 0
    failed = 0
    errors = 0
    results = []

    print("=" * 72)
    print("  ZILLOW ESTIMATE AGENT -- INTEGRATION TESTS")
    print(f"  Endpoint : {API_URL}")
    print(f"  Tolerance: +/-{TOLERANCE_PERCENT}%")
    print("=" * 72)

    for i, tc in enumerate(TEST_CASES, 1):
        label = tc["address_hint"]
        expected = tc["expected_zestimate"]

        print(f"\n[{i}/{len(TEST_CASES)}] {label}")
        print(f"  Expected : {fmt_price(expected)}")

        try:
            resp = requests.post(
                API_URL,
                json={"query": tc["query"]},
                timeout=TIMEOUT,
            )

            if resp.status_code != 200:
                print(f"  [FAIL] HTTP {resp.status_code}: {resp.text[:200]}")
                failed += 1
                results.append(("FAIL", label, f"HTTP {resp.status_code}"))
                continue

            data = resp.json()

            if not data.get("success"):
                err = data.get("error", "unknown error")
                print(f"  [FAIL] API error: {err}")
                failed += 1
                results.append(("FAIL", label, err))
                continue

            if data.get("response_type") != "property_estimate":
                print(f"  [FAIL] Response type is '{data.get('response_type')}', expected 'property_estimate'")
                failed += 1
                results.append(("FAIL", label, "wrong response_type"))
                continue

            actual = data.get("zestimate")
            if actual is None:
                print("  [FAIL] No zestimate in response")
                failed += 1
                results.append(("FAIL", label, "no zestimate"))
                continue

            match = within_tolerance(actual, expected, TOLERANCE_PERCENT)
            diff_pct = ((actual - expected) / expected) * 100

            if match:
                print(f"  Actual   : {fmt_price(actual)} ({diff_pct:+.1f}%)")
                print(f"  [PASS]")
                passed += 1
                results.append(("PASS", label, fmt_price(actual)))
            else:
                print(f"  Actual   : {fmt_price(actual)} ({diff_pct:+.1f}%)")
                print(f"  [FAIL] outside +/-{TOLERANCE_PERCENT}% tolerance")
                failed += 1
                results.append(("FAIL", label, f"{fmt_price(actual)} ({diff_pct:+.1f}%)"))

            if verbose:
                print(f"  Address  : {data.get('address', 'N/A')}")
                print(f"  Radius   : {data.get('radius', 'N/A')} mile(s)")
                if data.get("conversational_response"):
                    snippet = data["conversational_response"][:120]
                    print(f"  AI Reply : {snippet}...")

        except requests.exceptions.ConnectionError:
            print("  [ERROR] Cannot connect to server. Is the backend running?")
            errors += 1
            results.append(("ERROR", label, "connection refused"))
        except requests.exceptions.Timeout:
            print("  [ERROR] Request timed out")
            errors += 1
            results.append(("ERROR", label, "timeout"))
        except Exception as exc:
            print(f"  [ERROR] {exc}")
            errors += 1
            results.append(("ERROR", label, str(exc)))

    # -- Summary ---------------------------------------------------------------
    total = passed + failed + errors
    print("\n" + "=" * 72)
    print("  RESULTS SUMMARY")
    print("=" * 72)

    for status, label, detail in results:
        icon = {"PASS": "[PASS]", "FAIL": "[FAIL]", "ERROR": "[ERR ]"}[status]
        print(f"  {icon}  {label:50s}  {detail}")

    print("-" * 72)
    print(f"  Total: {total}  |  Passed: {passed}  |  Failed: {failed}  |  Errors: {errors}")
    print("=" * 72)

    return 0 if (failed == 0 and errors == 0) else 1


if __name__ == "__main__":
    verbose = "--verbose" in sys.argv or "-v" in sys.argv
    exit_code = run_tests(verbose=verbose)
    sys.exit(exit_code)
