# SafeDistrict AI — Evaluation Harness

## What it measures

The harness runs 20 hand-authored golden queries against a live `SafeDistrictAgent`
instance and checks three properties for each response:

| Check | What it tests |
|---|---|
| **Routing accuracy** | Did the agent call the right tool? (`rag` / `anomaly` / `compare`) |
| **Grounding** | Does the answer contain the expected NCRB 2023 facts? |
| **Hallucination** | Does the answer stay free of fabricated numbers or wrong attributions? |

A test case passes only when all three checks pass.

## Golden dataset breakdown

| Category | Count | What they probe |
|---|---|---|
| RAG | 5 | General safety questions — verified numbers from NCRB 2023 |
| Anomaly | 5 | Crime-spike / outlier questions — `detect_anomalies_tool` routing |
| Compare | 5 | Two- or three-city comparison questions — `compare_cities_tool` routing |
| Edge cases | 5 | Unknown city, meta/provenance questions, multi-city, state-level queries |

## How to run

From the repo root:

```bash
python eval/eval_runner.py
```

The runner prints a live progress line for each query, then a full results table
and a summary block:

```
  [01/20] Is Delhi City safe for women?
         → PASS  route=rag  grnd=✓  hall=✓
  ...

──────────────────────────────────────────────────────────────
 #  QUESTION                           ROUTE       GRND  HALL  RESULT
──────────────────────────────────────────────────────────────
 1  Is Delhi City safe for women?      ✓ rag        ✓     ✓    PASS
 ...

SUMMARY
  Total passed  : 18/20
  Routing       : 19/20  (95.0%)
  Grounding     : 18/20  (90.0%)
  Hallucination : 20/20  (100.0%)
```

## Regression gate

**Exit code 1** is returned if routing accuracy falls below **80 %** (fewer than
16 of 20 queries routed correctly).  This makes the harness CI-friendly:

```bash
python eval/eval_runner.py && echo "OK" || echo "REGRESSION"
```

## Rate-limit tuning

By default the runner sleeps **2 seconds** between API calls.  If you are on
the Groq free tier (70 000 tokens/minute), increase `SLEEP_BETWEEN_CALLS` at
the top of `eval_runner.py` to **15** to avoid 429 errors.

## Adding test cases

Edit `eval/golden_queries.py` and append entries to `GOLDEN_DATASET`.  Each
entry follows this schema:

```python
{
    "question":          str,          # natural-language question
    "expected_route":    "rag" | "anomaly" | "compare",
    "must_contain":      list[str],    # substrings that must appear in the answer
    "must_not_contain":  list[str],    # substrings that must NOT appear (hallucinations)
}
```

Matching is case-insensitive substring search.
