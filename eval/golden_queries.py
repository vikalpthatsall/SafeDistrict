"""
golden_queries.py — 20 hand-authored test cases for SafeDistrictAgent.

Each entry is a dict with:
  question          str        — natural-language input to the agent
  expected_route    str        — "rag" | "anomaly" | "compare"
  must_contain      list[str]  — substrings the answer MUST include (grounding)
  must_not_contain  list[str]  — substrings the answer MUST NOT include (hallucination)

Verified NCRB 2023 facts used:
  Delhi City  : 506 murders, 1088 rapes, 1832.6 crimes/lakh
  Bengaluru   : 206 murders, 1203 kidnappings, 337.3 crimes/lakh
  Jaipur      : 573 rapes, 916.7 crimes/lakh
  Mumbai      : 196 rapes, 367.3 crimes/lakh
  Kolkata     : 78.2 crimes/lakh (lowest metro)
  Patna       : 5.2 murders/lakh (highest verified murder rate)
"""

GOLDEN_DATASET = [
    # ─── 5 RAG queries ───────────────────────────────────────────────────────
    {
        "question": "Is Delhi City safe for women?",
        "expected_route": "rag",
        "must_contain": ["1088", "rape", "Delhi"],
        "must_not_contain": ["4247", "fabricated"],
    },
    {
        "question": "How many kidnapping cases were reported in Bengaluru in 2023?",
        "expected_route": "rag",
        "must_contain": ["1203", "Bengaluru", "kidnapping"],
        "must_not_contain": ["fabricated"],
    },
    {
        "question": "What is Kolkata's crime rate per lakh population?",
        "expected_route": "rag",
        "must_contain": ["78.2", "Kolkata"],
        "must_not_contain": ["1832", "fabricated"],
    },
    {
        "question": "How many murders were reported in Delhi City in 2023?",
        "expected_route": "rag",
        "must_contain": ["506", "Delhi", "murder"],
        "must_not_contain": ["2500", "fabricated"],
    },
    {
        "question": "How many rape cases did Jaipur report in 2023?",
        "expected_route": "rag",
        "must_contain": ["573", "Jaipur", "rape"],
        "must_not_contain": ["1500", "fabricated"],
    },
    # ─── 5 Anomaly queries ───────────────────────────────────────────────────
    {
        "question": "Are there any unusual crime spikes in Indian cities?",
        "expected_route": "anomaly",
        "must_contain": ["Crime spike analysis", "score"],
        "must_not_contain": ["fabricated"],
    },
    {
        "question": "Which cities have anomalous crime levels compared to the national trend?",
        "expected_route": "anomaly",
        "must_contain": ["Crime spike analysis", "crimes/lakh"],
        "must_not_contain": ["fabricated"],
    },
    {
        "question": "Show me cities with crime outliers or significant crime spikes",
        "expected_route": "anomaly",
        "must_contain": ["Crime spike analysis"],
        "must_not_contain": ["fabricated"],
    },
    {
        "question": "Is there any city showing an unusual surge in crime?",
        "expected_route": "anomaly",
        "must_contain": ["Crime spike analysis", "score"],
        "must_not_contain": ["fabricated"],
    },
    {
        "question": "Which Indian city has the most extreme crime anomaly score?",
        "expected_route": "anomaly",
        "must_contain": ["Crime spike analysis", "crimes/lakh"],
        "must_not_contain": ["fabricated"],
    },
    # ─── 5 Compare queries ───────────────────────────────────────────────────
    {
        "question": "Compare Pune and Mumbai for safety",
        "expected_route": "compare",
        "must_contain": ["Pune", "Mumbai", "ranked safest first"],
        "must_not_contain": ["fabricated"],
    },
    {
        "question": "Is Bengaluru or Hyderabad safer for families?",
        "expected_route": "compare",
        "must_contain": ["Bengaluru", "Hyderabad", "ranked safest first"],
        "must_not_contain": ["fabricated"],
    },
    {
        "question": "Compare Delhi and Kolkata in terms of crime levels",
        "expected_route": "compare",
        "must_contain": ["Delhi", "Kolkata", "ranked safest first"],
        "must_not_contain": ["fabricated"],
    },
    {
        "question": "Which is safer, Jaipur or Lucknow?",
        "expected_route": "compare",
        "must_contain": ["Jaipur", "Lucknow", "ranked safest first"],
        "must_not_contain": ["fabricated"],
    },
    {
        "question": "Should I move to Chennai or Patna? Which city is safer?",
        "expected_route": "compare",
        "must_contain": ["Chennai", "Patna", "ranked safest first"],
        "must_not_contain": ["fabricated"],
    },
    # ─── 5 Edge cases ────────────────────────────────────────────────────────
    {
        # City not in the dataset — graceful RAG fallback expected
        "question": "Is Shimla safe for relocation?",
        "expected_route": "rag",
        "must_contain": [],
        "must_not_contain": ["fabricated", "99999"],
    },
    {
        # Meta question about data provenance
        "question": "What data source does SafeDistrict use and what year is the crime data?",
        "expected_route": "rag",
        "must_contain": ["2023", "NCRB"],
        "must_not_contain": ["fabricated", "2019"],
    },
    {
        # Three-city comparison — tests multi-city compare path
        "question": "Compare Mumbai, Pune, and Nagpur for safety",
        "expected_route": "compare",
        "must_contain": ["Mumbai", "Pune", "Nagpur"],
        "must_not_contain": ["fabricated"],
    },
    {
        # Women-safety ranking — should surface Delhi City's verified stat
        "question": "Which Indian metro city has the highest number of rape cases?",
        "expected_route": "rag",
        "must_contain": ["Delhi", "1088"],
        "must_not_contain": ["fabricated"],
    },
    {
        # State-level safety query
        "question": "Which cities in Maharashtra should I be most cautious about?",
        "expected_route": "rag",
        "must_contain": ["Maharashtra"],
        "must_not_contain": ["fabricated"],
    },
]
