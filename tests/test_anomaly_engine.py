import pandas as pd
import pytest

from backend.anomaly_engine import AnomalyEngine, AnomalyResult


@pytest.fixture
def synthetic_df() -> pd.DataFrame:
    normal_rows = [
        {
            "city": f"City_{i}",
            "state": "StateA",
            "year": 2023,
            "murder": 8 + i,
            "rape": 15 + i,
            "kidnapping": 10 + i,
            "robbery": 30 + i,
            "burglary": 45 + i,
            "vehicle_theft": 20 + i,
            "crimes_per_lakh": 150 + 5 * i,
            "total_ipc": 200 + 10 * i,
        }
        for i in range(8)
    ]
    outlier_row = {
        "city": "City_Outlier",
        "state": "StateB",
        "year": 2023,
        "murder": 500,
        "rape": 800,
        "kidnapping": 400,
        "robbery": 900,
        "burglary": 1200,
        "vehicle_theft": 700,
        "crimes_per_lakh": 5000,
        "total_ipc": 4000,
    }
    return pd.DataFrame(normal_rows + [outlier_row])


def test_detect_before_fit_raises(synthetic_df: pd.DataFrame) -> None:
    engine = AnomalyEngine()
    with pytest.raises(RuntimeError):
        engine.detect(synthetic_df)


def test_fit_on_empty_df_raises() -> None:
    engine = AnomalyEngine()
    with pytest.raises(ValueError):
        engine.fit(pd.DataFrame())


def test_detect_flags_planted_outlier(synthetic_df: pd.DataFrame) -> None:
    engine = AnomalyEngine()
    engine.fit(synthetic_df)
    anomalies = engine.detect(synthetic_df)
    assert "City_Outlier" in [a.city for a in anomalies]


def test_compare_cities_sorted_and_skips_unknown(synthetic_df: pd.DataFrame) -> None:
    engine = AnomalyEngine()
    engine.fit(synthetic_df)
    result = engine.compare_cities(synthetic_df, ["City_0", "City_1", "Nowhereville"])
    cities = [r["city"] for r in result]
    assert "Nowhereville" not in cities
    assert len(result) == 2
    scores = [r["safety_score"] for r in result]
    assert scores == sorted(scores, reverse=True)


def test_get_city_safety_score_unknown_city(synthetic_df: pd.DataFrame) -> None:
    engine = AnomalyEngine()
    result = engine.get_city_safety_score(synthetic_df, "Nowhereville")
    assert result["state"] == "Unknown"
    assert result["risk_level"] == "Unknown"
    assert result["safety_score"] is None
    assert result["avg_crimes_per_lakh"] is None
    assert result["women_risk_score"] is None
    assert result["anomaly_count"] == 0


def test_anomaly_result_is_severe_boundary() -> None:
    not_severe = AnomalyResult(
        city="City_X", state="StateA", year=2023,
        crime_type="test", actual_value=1.0, anomaly_score=0.7,
    )
    severe = AnomalyResult(
        city="City_X", state="StateA", year=2023,
        crime_type="test", actual_value=1.0, anomaly_score=0.70001,
    )
    assert not_severe.is_severe is False
    assert severe.is_severe is True
