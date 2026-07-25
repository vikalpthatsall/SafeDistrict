import pytest

from backend.data_loader import CrimeDataLoader


@pytest.fixture(scope="module")
def loader() -> CrimeDataLoader:
    return CrimeDataLoader()


def test_df_loads_and_nonempty(loader: CrimeDataLoader) -> None:
    df = loader.df
    assert not df.empty
    assert len(df) in (19, 53)
    print(f"Loaded {len(df)} rows (fallback=19, full=53)")


def test_data_quality_values(loader: CrimeDataLoader) -> None:
    allowed = {"real", "derived", "estimated", "national"}
    assert set(loader.df["data_quality"].unique()) <= allowed


def test_delhi_city_verified_counts(loader: CrimeDataLoader) -> None:
    row = loader.get_city("Delhi City").iloc[0]
    assert row["murder"] == 506
    assert row["rape"] == 1088


def test_get_city_unknown_returns_empty(loader: CrimeDataLoader) -> None:
    result = loader.get_city("nonexistent city")
    assert result.empty


def test_get_top_crimes_n_and_sorted(loader: CrimeDataLoader) -> None:
    top = loader.get_top_crimes(5)
    assert len(top) == 5
    rates = top["crimes_per_lakh"].tolist()
    assert rates == sorted(rates, reverse=True)
