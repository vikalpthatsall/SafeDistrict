"""
anomaly_engine.py — IsolationForest-based anomaly detection for SafeDistrict AI.

Exposes AnomalyEngine (fit/detect/compare) and a standalone women-safety helper.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass, field

import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler


# ---------------------------------------------------------------------------
# AnomalyResult dataclass
# ---------------------------------------------------------------------------

@dataclass
class AnomalyResult:
    """Single anomalous observation returned by AnomalyEngine.detect()."""

    city: str
    state: str
    year: int
    crime_type: str
    actual_value: float
    anomaly_score: float  # 0–1, higher = more anomalous
    is_severe: bool = field(init=False)

    def __post_init__(self) -> None:
        """Derive is_severe from anomaly_score threshold."""
        self.is_severe = self.anomaly_score > 0.7

    def __str__(self) -> str:
        """Return a readable one-line summary."""
        severity = "SEVERE" if self.is_severe else "moderate"
        return (
            f"[{severity}] {self.city} ({self.state}) | "
            f"{self.crime_type} = {self.actual_value:.1f} | "
            f"score={self.anomaly_score:.3f}"
        )

    def __repr__(self) -> str:
        """Return a debug-friendly representation."""
        return (
            f"AnomalyResult(city={self.city!r}, state={self.state!r}, "
            f"year={self.year}, crime_type={self.crime_type!r}, "
            f"actual_value={self.actual_value}, "
            f"anomaly_score={self.anomaly_score:.4f}, "
            f"is_severe={self.is_severe})"
        )

    def __lt__(self, other: AnomalyResult) -> bool:
        """Enable sorted() by anomaly_score ascending."""
        return self.anomaly_score < other.anomaly_score


# ---------------------------------------------------------------------------
# AnomalyEngine
# ---------------------------------------------------------------------------

_FEATURE_COLS = [
    "murder", "rape", "kidnapping", "robbery",
    "burglary", "vehicle_theft", "crimes_per_lakh",
]


class AnomalyEngine:
    """IsolationForest-based anomaly detector over city-level crime data."""

    def __init__(self, contamination: float = 0.1) -> None:
        """Initialise the engine with an unfitted IsolationForest and scaler.

        Parameters
        ----------
        contamination : float
            Expected proportion of anomalies in the dataset (default 0.1).
        """
        self._forest = IsolationForest(
            contamination=contamination,
            random_state=42,
            n_estimators=100,
        )
        self._scaler = StandardScaler()
        self.is_fitted: bool = False
        self.feature_cols: list[str] | None = None

    # ------------------------------------------------------------------
    # fit
    # ------------------------------------------------------------------

    def fit(self, df: pd.DataFrame) -> None:
        """Fit the scaler and IsolationForest on the provided DataFrame.

        Parameters
        ----------
        df : pd.DataFrame
            Must contain all columns in _FEATURE_COLS.
        """
        if df.empty:
            raise ValueError("Cannot fit on an empty DataFrame.")

        self.feature_cols = _FEATURE_COLS
        X = df[self.feature_cols].values.astype(float)
        X_scaled = self._scaler.fit_transform(X)
        self._forest.fit(X_scaled)
        self.is_fitted = True

    # ------------------------------------------------------------------
    # detect
    # ------------------------------------------------------------------

    def detect(self, df: pd.DataFrame) -> list[AnomalyResult]:
        """Detect anomalous cities and return sorted AnomalyResult list.

        Parameters
        ----------
        df : pd.DataFrame
            DataFrame with the same feature columns used during fit().

        Returns
        -------
        list[AnomalyResult]
            Anomalous rows only, sorted by anomaly_score descending.

        Raises
        ------
        RuntimeError
            If the engine has not been fitted yet.
        """
        if not self.is_fitted:
            raise RuntimeError("AnomalyEngine must be fitted before calling detect().")
        if df.empty:
            return []

        X = df[self.feature_cols].values.astype(float)
        X_scaled = self._scaler.transform(X)

        predictions = self._forest.predict(X_scaled)          # -1 or 1
        raw_scores = self._forest.decision_function(X_scaled) # higher = more normal

        score_min, score_max = raw_scores.min(), raw_scores.max()
        if score_max == score_min:
            normalized = np.zeros_like(raw_scores)
        else:
            normalized = (raw_scores - score_min) / (score_max - score_min)
        anomaly_scores = 1.0 - normalized  # invert: high = more anomalous

        results: list[AnomalyResult] = []
        for idx, (pred, score) in enumerate(zip(predictions, anomaly_scores)):
            if pred != -1:
                continue
            row = df.iloc[idx]
            results.append(
                AnomalyResult(
                    city=str(row["city"]),
                    state=str(row["state"]),
                    year=int(row["year"]),
                    crime_type="multi-feature",
                    actual_value=float(row["crimes_per_lakh"]),
                    anomaly_score=float(score),
                )
            )

        return sorted(results, reverse=True)

    # ------------------------------------------------------------------
    # get_city_safety_score
    # ------------------------------------------------------------------

    def get_city_safety_score(self, df: pd.DataFrame, city: str) -> dict:
        """Compute a composite safety score and risk metadata for a city.

        Parameters
        ----------
        df : pd.DataFrame
            Full crime DataFrame.
        city : str
            City name (case-insensitive match).

        Returns
        -------
        dict
            Keys: city, state, avg_crimes_per_lakh, women_risk_score,
                  safety_score, risk_level, anomaly_count.
        """
        city_df = df[df["city"].str.lower() == city.lower()]
        if city_df.empty:
            return {
                "city": city,
                "state": "Unknown",
                "avg_crimes_per_lakh": None,
                "women_risk_score": None,
                "safety_score": None,
                "risk_level": "Unknown",
                "anomaly_count": 0,
            }

        avg_crimes = float(city_df["crimes_per_lakh"].mean())
        women_risk = float(
            ((city_df["rape"] + city_df["kidnapping"]) / city_df["total_ipc"]).mean()
        )

        global_max = float(df["crimes_per_lakh"].max())
        raw_safety = 10.0 - (avg_crimes / global_max * 10.0) if global_max > 0 else 10.0
        safety_score = round(max(0.0, min(10.0, raw_safety)), 2)

        if safety_score >= 7:
            risk_level = "Low"
        elif safety_score >= 4:
            risk_level = "Medium"
        else:
            risk_level = "High"

        anomaly_count = 0
        if self.is_fitted:
            anomalies = self.detect(df)
            anomaly_count = sum(1 for a in anomalies if a.city.lower() == city.lower())

        return {
            "city": str(city_df.iloc[0]["city"]),
            "state": str(city_df.iloc[0]["state"]),
            "avg_crimes_per_lakh": round(avg_crimes, 2),
            "women_risk_score": round(women_risk, 4),
            "safety_score": safety_score,
            "risk_level": risk_level,
            "anomaly_count": anomaly_count,
        }

    # ------------------------------------------------------------------
    # compare_cities
    # ------------------------------------------------------------------

    def compare_cities(self, df: pd.DataFrame, cities: list[str]) -> list[dict]:
        """Return safety profiles for multiple cities, sorted safest-first.

        Parameters
        ----------
        df : pd.DataFrame
            Full crime DataFrame.
        cities : list[str]
            City names to compare; cities not found in df are skipped.

        Returns
        -------
        list[dict]
            Safety dicts sorted by safety_score descending.
        """
        results = []
        for city in cities:
            profile = self.get_city_safety_score(df, city)
            if profile["safety_score"] is None:
                continue
            results.append(profile)
        return sorted(results, key=lambda d: d["safety_score"], reverse=True)

    # ------------------------------------------------------------------
    # get_state_summary
    # ------------------------------------------------------------------

    def get_state_summary(self, df: pd.DataFrame, state: str) -> dict:
        """Summarise crime statistics for all cities in a state.

        Parameters
        ----------
        df : pd.DataFrame
            Full crime DataFrame.
        state : str
            State name (case-insensitive match).

        Returns
        -------
        dict
            Keys: state, city_count, avg_crimes_per_lakh, safest_city,
                  most_dangerous_city, total_anomalies_in_state.
        """
        state_df = df[df["state"].str.lower() == state.lower()]
        if state_df.empty:
            return {
                "state": state,
                "city_count": 0,
                "avg_crimes_per_lakh": None,
                "safest_city": None,
                "most_dangerous_city": None,
                "total_anomalies_in_state": 0,
            }

        safest = state_df.loc[state_df["crimes_per_lakh"].idxmin(), "city"]
        most_dangerous = state_df.loc[state_df["crimes_per_lakh"].idxmax(), "city"]

        total_anomalies = 0
        if self.is_fitted:
            state_cities = set(state_df["city"].str.lower())
            anomalies = self.detect(df)
            total_anomalies = sum(1 for a in anomalies if a.city.lower() in state_cities)

        return {
            "state": state,
            "city_count": len(state_df),
            "avg_crimes_per_lakh": round(float(state_df["crimes_per_lakh"].mean()), 2),
            "safest_city": str(safest),
            "most_dangerous_city": str(most_dangerous),
            "total_anomalies_in_state": total_anomalies,
        }

    def __repr__(self) -> str:
        """Return a debug-friendly representation of the engine state."""
        return (
            f"AnomalyEngine("
            f"fitted={self.is_fitted}, "
            f"contamination={self._forest.contamination}, "
            f"n_estimators={self._forest.n_estimators}, "
            f"features={self.feature_cols})"
        )


# ---------------------------------------------------------------------------
# Standalone women-safety anomaly detector
# ---------------------------------------------------------------------------

def detect_women_safety_anomalies(
    df: pd.DataFrame,
    engine: AnomalyEngine,
    top_n: int = 5,
) -> list[AnomalyResult]:
    """Detect cities anomalous specifically on women-safety crimes.

    Fits a fresh IsolationForest on only rape and kidnapping columns,
    independent of the main engine.

    Parameters
    ----------
    df : pd.DataFrame
        Full crime DataFrame.
    engine : AnomalyEngine
        Used only for its contamination parameter.
    top_n : int
        Maximum number of results to return (default 5).

    Returns
    -------
    list[AnomalyResult]
        Top-n anomalous cities sorted by women-safety anomaly score descending.
    """
    if df.empty:
        return []

    women_cols = ["rape", "kidnapping"]
    X = df[women_cols].values.astype(float)

    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    forest = IsolationForest(
        contamination=engine._forest.contamination,
        random_state=42,
        n_estimators=100,
    )
    forest.fit(X_scaled)

    predictions = forest.predict(X_scaled)
    raw_scores = forest.decision_function(X_scaled)

    score_min, score_max = raw_scores.min(), raw_scores.max()
    if score_max == score_min:
        normalized = np.zeros_like(raw_scores)
    else:
        normalized = (raw_scores - score_min) / (score_max - score_min)
    anomaly_scores = 1.0 - normalized

    results: list[AnomalyResult] = []
    for idx, (pred, score) in enumerate(zip(predictions, anomaly_scores)):
        if pred != -1:
            continue
        row = df.iloc[idx]
        results.append(
            AnomalyResult(
                city=str(row["city"]),
                state=str(row["state"]),
                year=int(row["year"]),
                crime_type="women-safety (rape+kidnapping)",
                actual_value=float(row["rape"] + row["kidnapping"]),
                anomaly_score=float(score),
            )
        )

    return sorted(results, reverse=True)[:top_n]


# ---------------------------------------------------------------------------
# Smoke-test entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    sys.path.insert(0, ".")
    from backend.data_loader import CrimeDataLoader

    loader = CrimeDataLoader()
    df = loader.df

    engine = AnomalyEngine()
    engine.fit(df)

    anomalies = engine.detect(df)
    print(f"\n{'='*60}")
    print(f"Total anomalies detected: {len(anomalies)}")
    print(f"{'='*60}")

    print("\n--- Top 5 Anomalies ---")
    for i, a in enumerate(anomalies[:5], 1):
        print(f"  {i}. {a}")

    compare_cities = ["Pune", "Mumbai", "Delhi City", "Bengaluru", "Jaipur"]
    print(f"\n--- City Comparison: {compare_cities} ---")
    comparison = engine.compare_cities(df, compare_cities)
    print(f"  {'City':<18} {'State':<20} {'Safety':>7} {'Risk':<8} {'Crimes/Lakh':>12} {'Anomalies':>10}")
    print(f"  {'-'*80}")
    for c in comparison:
        print(
            f"  {c['city']:<18} {c['state']:<20} "
            f"{c['safety_score']:>7.2f} {c['risk_level']:<8} "
            f"{c['avg_crimes_per_lakh']:>12.2f} {c['anomaly_count']:>10}"
        )

    print("\n--- Maharashtra State Summary ---")
    summary = engine.get_state_summary(df, "Maharashtra")
    for k, v in summary.items():
        print(f"  {k}: {v}")

    print("\n--- Top 5 Women Safety Anomalies ---")
    women_anomalies = detect_women_safety_anomalies(df, engine, top_n=5)
    if women_anomalies:
        for i, a in enumerate(women_anomalies, 1):
            print(f"  {i}. {a}")
    else:
        print("  No women-safety anomalies detected.")
