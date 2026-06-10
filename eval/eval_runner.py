"""
eval_runner.py — Offline evaluation harness for SafeDistrictAgent.

Usage:
    python eval/eval_runner.py

Exit codes:
    0 — all gates passed  (routing accuracy >= 80%)
    1 — regression gate failed (routing accuracy < 80%)
"""

from __future__ import annotations

import os
import sys
import time

# Repo root must be in sys.path so backend imports resolve.
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
# eval/ must be in sys.path so golden_queries imports resolve.
sys.path.insert(0, os.path.dirname(__file__))

from dotenv import load_dotenv

load_dotenv()

from backend.agent import SafeDistrictAgent
from golden_queries import GOLDEN_DATASET

# Delay between API calls (seconds).  Raise to 15 on Groq free tier.
SLEEP_BETWEEN_CALLS: int = 2

# Routing accuracy threshold below which exit code 1 is returned.
ROUTING_GATE: float = 80.0


# ---------------------------------------------------------------------------
# Core evaluator
# ---------------------------------------------------------------------------

def evaluate_case(agent: SafeDistrictAgent, case: dict) -> dict:
    """Run one golden query and return a result dict."""
    question = case["question"]
    expected_route = case["expected_route"]
    must_contain = case["must_contain"]
    must_not_contain = case["must_not_contain"]

    try:
        response = agent.run(question)
        answer = response.get("answer", "")
        actual_route = response.get("query_type", "unknown")
    except Exception as exc:
        answer = ""
        actual_route = "error"
        print(f"    ERROR during agent.run(): {exc}")

    answer_lower = answer.lower()

    route_ok = actual_route == expected_route
    grounding_failures = [s for s in must_contain if s.lower() not in answer_lower]
    grounding_ok = len(grounding_failures) == 0
    hallucination_hits = [s for s in must_not_contain if s.lower() in answer_lower]
    hallucination_ok = len(hallucination_hits) == 0

    return {
        "question": question,
        "expected_route": expected_route,
        "actual_route": actual_route,
        "route_ok": route_ok,
        "grounding_ok": grounding_ok,
        "grounding_failures": grounding_failures,
        "hallucination_ok": hallucination_ok,
        "hallucination_hits": hallucination_hits,
        "passed": route_ok and grounding_ok and hallucination_ok,
        "answer": answer,
    }


# ---------------------------------------------------------------------------
# Reporting
# ---------------------------------------------------------------------------

_COL = {
    "idx": 4,
    "question": 52,
    "route": 12,
    "grnd": 5,
    "hall": 5,
    "result": 6,
}
_LINE = "─" * 93


def _check(flag: bool) -> str:
    return "✓" if flag else "✗"


def print_results_table(results: list[dict]) -> None:
    print(_LINE)
    print(
        f" {'#':>{_COL['idx']}}  "
        f"{'QUESTION':<{_COL['question']}}  "
        f"{'ROUTE':<{_COL['route']}}  "
        f"{'GRND':>{_COL['grnd']}}  "
        f"{'HALL':>{_COL['hall']}}  "
        f"{'RESULT':>{_COL['result']}}"
    )
    print(_LINE)
    for i, r in enumerate(results, 1):
        route_cell = f"{_check(r['route_ok'])} {r['actual_route']:<8}"
        q = r["question"]
        if len(q) > _COL["question"]:
            q = q[: _COL["question"] - 1] + "…"
        print(
            f" {i:>{_COL['idx']}}  "
            f"{q:<{_COL['question']}}  "
            f"{route_cell:<{_COL['route']}}  "
            f"{_check(r['grounding_ok']):>{_COL['grnd']}}  "
            f"{_check(r['hallucination_ok']):>{_COL['hall']}}  "
            f"{'PASS' if r['passed'] else 'FAIL':>{_COL['result']}}"
        )
    print(_LINE)


def print_failures(results: list[dict]) -> None:
    failed = [r for r in results if not r["passed"]]
    if not failed:
        return
    print("\nFAILURE DETAIL")
    for r in failed:
        print(f"\n  Q: {r['question']}")
        if not r["route_ok"]:
            print(f"     routing   expected={r['expected_route']}  got={r['actual_route']}")
        if not r["grounding_ok"]:
            print(f"     grounding missing: {r['grounding_failures']}")
        if not r["hallucination_ok"]:
            print(f"     hallucination found: {r['hallucination_hits']}")


def print_summary(results: list[dict]) -> float:
    total = len(results)
    passed = sum(1 for r in results if r["passed"])
    routing = sum(1 for r in results if r["route_ok"])
    grounding = sum(1 for r in results if r["grounding_ok"])
    hallucination = sum(1 for r in results if r["hallucination_ok"])

    routing_pct = routing / total * 100

    print("\nSUMMARY")
    print(f"  Total passed  : {passed}/{total}")
    print(f"  Routing       : {routing}/{total}  ({routing_pct:.1f}%)")
    print(f"  Grounding     : {grounding}/{total}  ({grounding / total * 100:.1f}%)")
    print(f"  Hallucination : {hallucination}/{total}  ({hallucination / total * 100:.1f}%)")

    return routing_pct


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def run_evaluation() -> None:
    total = len(GOLDEN_DATASET)
    print(f"Loading SafeDistrictAgent…")
    agent = SafeDistrictAgent()
    print(f"Agent ready.  Running {total} golden queries  (sleep={SLEEP_BETWEEN_CALLS}s between calls)\n")

    results: list[dict] = []

    for i, case in enumerate(GOLDEN_DATASET, 1):
        if i > 1:
            time.sleep(SLEEP_BETWEEN_CALLS)
        print(f"  [{i:02d}/{total}] {case['question'][:70]}")
        result = evaluate_case(agent, case)
        results.append(result)
        status = "PASS" if result["passed"] else "FAIL"
        print(f"         → {status}  route={result['actual_route']}  grnd={_check(result['grounding_ok'])}  hall={_check(result['hallucination_ok'])}")

    print()
    print_results_table(results)
    print_failures(results)
    routing_pct = print_summary(results)

    if routing_pct < ROUTING_GATE:
        print(
            f"\nREGRESSION GATE FAILED: routing accuracy {routing_pct:.1f}% < {ROUTING_GATE:.0f}%"
        )
        sys.exit(1)

    print(f"\nAll gates passed.")


if __name__ == "__main__":
    run_evaluation()
