"""
data_loader.py — NCRB 2023 city-level crime data with tiered data quality.

Tiered quality for crime counts:
  real      — exact count from NCRB 2023 tables
  derived   — computed from verified NCRB 2023 murder rate per lakh × population
  estimated — state-level NCRB ratio × total IPC (state-differentiated, not national)
  national  — national average ratio × total IPC (fallback only)
"""

import logging
import sys

import pandas as pd

sys.path.insert(0, ".")
from data.processed.ncrb_2023_verified import (
    NCRB_2023_CRIME_RATE_PER_LAKH,
    NCRB_2023_KEY_FINDINGS,
    NCRB_2023_KIDNAPPING,
    NCRB_2023_MURDER_RATE_PER_LAKH,
    NCRB_2023_MURDERS,
    NCRB_2023_NATIONAL_RATIOS,
    NCRB_2023_RAPE,
    NCRB_2023_STATE_RATIOS,
)

logger = logging.getLogger(__name__)

_CITY_STATE = {
    "Agra": "Uttar Pradesh",
    "Ahmedabad": "Gujarat",
    "Amritsar": "Punjab",
    "Asansol": "West Bengal",
    "Aurangabad": "Maharashtra",
    "Bengaluru": "Karnataka",
    "Bhopal": "Madhya Pradesh",
    "Chennai": "Tamil Nadu",
    "Coimbatore": "Tamil Nadu",
    "Delhi": "Delhi",
    "Delhi City": "Delhi",
    "Chandigarh City": "Chandigarh",
    "Durg-Bhilainagar": "Chhattisgarh",
    "Gwalior": "Madhya Pradesh",
    "Jamshedpur": "Jharkhand",
    "Kannur": "Kerala",
    "Kollam": "Kerala",
    "Kota": "Rajasthan",
    "Malappuram": "Kerala",
    "Nasik": "Maharashtra",
    "Prayagraj": "Uttar Pradesh",
    "Thiruvananthapuram": "Kerala",
    "Thrissur": "Kerala",
    "Tiruchirapalli": "Tamil Nadu",
    "Vasai Virar": "Maharashtra",
    "Vishakhapatnam": "Andhra Pradesh",
    "Dhanbad": "Jharkhand",
    "Faridabad": "Haryana",
    "Ghaziabad": "Uttar Pradesh",
    "Hyderabad": "Telangana",
    "Indore": "Madhya Pradesh",
    "Jaipur": "Rajasthan",
    "Jabalpur": "Madhya Pradesh",
    "Jodhpur": "Rajasthan",
    "Kanpur": "Uttar Pradesh",
    "Kochi": "Kerala",
    "Kolkata": "West Bengal",
    "Kozhikode": "Kerala",
    "Lucknow": "Uttar Pradesh",
    "Ludhiana": "Punjab",
    "Madurai": "Tamil Nadu",
    "Meerut": "Uttar Pradesh",
    "Mumbai": "Maharashtra",
    "Mysuru": "Karnataka",
    "Nagpur": "Maharashtra",
    "Nashik": "Maharashtra",
    "Patna": "Bihar",
    "Pune": "Maharashtra",
    "Raipur": "Chhattisgarh",
    "Rajkot": "Gujarat",
    "Ranchi": "Jharkhand",
    "Srinagar": "Jammu & Kashmir",
    "Surat": "Gujarat",
    "Thane": "Maharashtra",
    "Tiruppur": "Tamil Nadu",
    "Vadodara": "Gujarat",
    "Varanasi": "Uttar Pradesh",
    "Vijayawada": "Andhra Pradesh",
    "Visakhapatnam": "Andhra Pradesh",
}

_CITY_POPULATION = {
    "Agra": 1585704,
    "Ahmedabad": 5570585,
    "Amritsar": 1132761,
    "Asansol": 1243414,
    "Aurangabad": 1175116,
    "Bengaluru": 8425970,
    "Bhopal": 1798218,
    "Chandigarh City": 960787,
    "Chennai": 4646732,
    "Coimbatore": 1601438,
    "Delhi": 11034555,
    "Delhi City": 11034555,
    "Dhanbad": 1195298,
    "Faridabad": 1403921,
    "Ghaziabad": 1636068,
    "Hyderabad": 6809970,
    "Indore": 1994397,
    "Jabalpur": 1267564,
    "Jaipur": 3046163,
    "Jodhpur": 1033918,
    "Kanpur": 2920067,
    "Kochi": 677381,
    "Kolkata": 4496694,
    "Kozhikode": 609224,
    "Lucknow": 2817105,
    "Ludhiana": 1618879,
    "Madurai": 1017865,
    "Meerut": 1305429,
    "Mumbai": 12442373,
    "Mysuru": 920550,
    "Nagpur": 2405421,
    "Nashik": 1486973,
    "Patna": 1684222,
    "Pune": 3124458,
    "Raipur": 1022615,
    "Rajkot": 1390640,
    "Ranchi": 1073440,
    "Srinagar": 1180570,
    "Surat": 4467797,
    "Thane": 1818872,
    "Tiruppur": 877778,
    "Vadodara": 1670806,
    "Varanasi": 1198491,
    "Vijayawada": 1048240,
    "Vishakhapatnam": 1728128,
    "Visakhapatnam": 1728128,
    "Durg-Bhilainagar": 1064077,
    "Gwalior": 1054420,
    "Jamshedpur": 629000,
    "Kannur": 699000,
    "Kollam": 394914,
    "Kota": 1001365,
    "Malappuram": 705000,
    "Nasik": 1486973,
    "Prayagraj": 1117094,
    "Thiruvananthapuram": 957730,
    "Thrissur": 487000,
    "Tiruchirapalli": 1021717,
    "Vasai Virar": 1221233,
}

# Precomputed fallback total IPC counts: NCRB_2023_CRIME_RATE_PER_LAKH × population / 100000
# Used when data/raw/ipc_crimes_citywise_2023.xlsx is not present.
_FALLBACK_TOTAL_IPC = {
    "Delhi City":  202218,
    "Jaipur":       27924,
    "Indore":       15306,
    "Kochi":         4244,
    "Patna":        10302,
    "Lucknow":      14677,
    "Nagpur":       12412,
    "Ghaziabad":     6839,
    "Kanpur":       11719,
    "Kozhikode":     2422,
    "Mumbai":       45700,
    "Ahmedabad":    20059,
    "Bengaluru":    28418,
    "Hyderabad":    18163,
    "Pune":          6852,
    "Surat":         9620,
    "Coimbatore":    3381,
    "Chennai":       9816,
    "Kolkata":       3516,
}

# Quality rank for computing overall row quality (lower = better)
_QUALITY_RANK = {"real": 0, "derived": 1, "estimated": 2, "national": 3}
_QUALITY_NAMES = ["real", "derived", "estimated", "national"]


def _lookup(city: str, d: dict):
    """Look up city in dict; handles 'Delhi City' → 'Delhi' alias."""
    val = d.get(city)
    if val is None and city == "Delhi City":
        val = d.get("Delhi")
    return val


def load_real_ncrb_data() -> pd.DataFrame:
    """Read NCRB 2023 city-wise IPC crimes from Excel, or fall back to precomputed totals.

    Returns
    -------
    pd.DataFrame
        Columns: city, cases_156_3, police_station_cases, total_ipc, _source.
        53 rows from Excel, or 19 rows from fallback dict.
    """
    try:
        df = pd.read_excel(
            "data/raw/ipc_crimes_citywise_2023.xlsx",
            skiprows=3,
            header=None,
        )
        df.columns = ["sl_no", "city", "cases_156_3", "police_station_cases", "total_ipc"]
        df = df.iloc[:-1].copy()
        df = df.drop(columns=["sl_no"])
        df["city"] = df["city"].str.strip()
        for col in ["cases_156_3", "police_station_cases", "total_ipc"]:
            df[col] = df[col].astype(int)
        df["_source"] = "excel"
        return df.reset_index(drop=True)
    except Exception:  # noqa: BLE001 — missing/malformed data/raw/ Excel (or missing openpyxl) all fall back to the 19-city dict the same way.
        rows = [
            {
                "city": city,
                "cases_156_3": 0,
                "police_station_cases": 0,
                "total_ipc": total,
                "_source": "fallback",
            }
            for city, total in _FALLBACK_TOTAL_IPC.items()
        ]
        return pd.DataFrame(rows)


def enrich_with_crime_breakdown(df: pd.DataFrame) -> pd.DataFrame:
    """Add tiered crime-type columns, quality flags, state, population, year, and rate.

    Murder uses verified counts where available, then derived from rate × population,
    then state-level ratios, then national ratios as last resort.
    Rape uses verified counts for Delhi/Jaipur/Mumbai; state ratios elsewhere.
    Kidnapping uses verified count for Bengaluru; state ratios elsewhere.
    All other crime types use state-differentiated ratios.

    Parameters
    ----------
    df : pd.DataFrame
        Raw DataFrame from load_real_ncrb_data().

    Returns
    -------
    pd.DataFrame
        Enriched DataFrame with quality columns and crime breakdowns.
    """
    df = df.copy()
    rows = []

    for _, row in df.iterrows():
        city = row["city"]
        state = _CITY_STATE.get(city, "Other")
        population = _CITY_POPULATION.get(city, 500000)
        total_ipc = int(row["total_ipc"])

        # crimes_per_lakh: use NCRB-verified rate if available, else compute
        verified_rate = _lookup(city, NCRB_2023_CRIME_RATE_PER_LAKH)
        crimes_per_lakh = (
            verified_rate
            if verified_rate is not None
            else round((total_ipc / population) * 100000, 2)
        )

        # state ratios (or national fallback)
        state_ratios = NCRB_2023_STATE_RATIOS.get(state)
        ratios = state_ratios if state_ratios else NCRB_2023_NATIONAL_RATIOS
        ratio_tier = "estimated" if state_ratios else "national"

        # --- murder ---
        real_murder = _lookup(city, NCRB_2023_MURDERS)
        if real_murder is not None:
            murder = real_murder
            murder_quality = "real"
        else:
            murder_rate = _lookup(city, NCRB_2023_MURDER_RATE_PER_LAKH)
            if murder_rate is not None:
                murder = round(murder_rate * population / 100000)
                murder_quality = "derived"
            else:
                murder = round(total_ipc * ratios["murder"])
                murder_quality = ratio_tier

        # --- rape ---
        real_rape = _lookup(city, NCRB_2023_RAPE)
        if real_rape is not None:
            rape = real_rape
            rape_quality = "real"
        else:
            rape = round(total_ipc * ratios["rape"])
            rape_quality = ratio_tier

        # --- kidnapping ---
        real_kidnapping = _lookup(city, NCRB_2023_KIDNAPPING)
        if real_kidnapping is not None:
            kidnapping = real_kidnapping
            kidnapping_quality = "real"
        else:
            kidnapping = round(total_ipc * ratios["kidnapping"])
            kidnapping_quality = ratio_tier

        # --- other crimes: always state-estimated ---
        robbery = round(total_ipc * ratios["robbery"])
        burglary = round(total_ipc * ratios["burglary"])
        vehicle_theft = round(total_ipc * ratios["vehicle_theft"])

        # overall row quality = worst of all tiers used
        worst = max(
            _QUALITY_RANK[murder_quality],
            _QUALITY_RANK[rape_quality],
            _QUALITY_RANK[kidnapping_quality],
            _QUALITY_RANK[ratio_tier],
        )
        data_quality = _QUALITY_NAMES[worst]

        out = {
            "city": city,
            "state": state,
            "year": 2023,
            "murder": murder,
            "rape": rape,
            "kidnapping": kidnapping,
            "robbery": robbery,
            "burglary": burglary,
            "vehicle_theft": vehicle_theft,
            "total_ipc": total_ipc,
            "population": population,
            "crimes_per_lakh": crimes_per_lakh,
            "murder_quality": murder_quality,
            "rape_quality": rape_quality,
            "kidnapping_quality": kidnapping_quality,
            "data_quality": data_quality,
        }
        if row.get("_source") == "excel":
            out["cases_156_3"] = int(row.get("cases_156_3", 0))
            out["police_station_cases"] = int(row.get("police_station_cases", 0))

        rows.append(out)

    result = pd.DataFrame(rows)

    core_cols = [
        "city", "state", "year",
        "murder", "rape", "kidnapping", "robbery", "burglary", "vehicle_theft",
        "total_ipc", "population", "crimes_per_lakh",
        "murder_quality", "rape_quality", "kidnapping_quality", "data_quality",
    ]
    extra_cols = [c for c in ["cases_156_3", "police_station_cases"] if c in result.columns]
    return result[core_cols + extra_cols]


def load_crime_data() -> pd.DataFrame:
    """Load, enrich, and return the full NCRB 2023 city-level crime DataFrame.

    Returns
    -------
    pd.DataFrame
        53-row (or 19-row fallback) DataFrame ready for RAG and anomaly detection.
    """
    df = load_real_ncrb_data()
    return enrich_with_crime_breakdown(df)


class CrimeDataLoader:
    """High-level query interface over the real NCRB 2023 city crime dataset.

    Attributes
    ----------
    df : pd.DataFrame
        Enriched city DataFrame produced by load_crime_data().
    key_findings : list[str]
        13 verified facts from NCRB Crime in India 2023.
    """

    def __init__(self) -> None:
        self.df: pd.DataFrame = load_crime_data()
        self.key_findings: list[str] = NCRB_2023_KEY_FINDINGS

    def get_state(self, state_name: str) -> pd.DataFrame:
        """Return all cities in the given state (case-insensitive)."""
        mask = self.df["state"].str.lower() == state_name.lower()
        return self.df[mask].reset_index(drop=True)

    def get_city(self, city_name: str) -> pd.DataFrame:
        """Return the row(s) for the given city (case-insensitive)."""
        mask = self.df["city"].str.lower() == city_name.lower()
        return self.df[mask].reset_index(drop=True)

    def get_top_crimes(self, n: int = 5) -> pd.DataFrame:
        """Return the n cities with the highest crimes_per_lakh rate."""
        return self.df.nlargest(n, "crimes_per_lakh").reset_index(drop=True)

    def get_women_risk_cities(self, n: int = 5) -> pd.DataFrame:
        """Return the n cities with the highest combined rape + kidnapping count."""
        df = self.df.copy()
        df["women_risk"] = df["rape"] + df["kidnapping"]
        return (
            df.nlargest(n, "women_risk")
            .drop(columns=["women_risk"])
            .reset_index(drop=True)
        )

    def __len__(self) -> int:
        return len(self.df)

    def __repr__(self) -> str:
        states = self.df["state"].nunique()
        return (
            f"CrimeDataLoader("
            f"cities={len(self)}, "
            f"states={states}, "
            f"year=2023, "
            f"source=NCRB 2023)"
        )


# ---------------------------------------------------------------------------
# Smoke-test entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    # Standalone smoke-test run (python -m backend.data_loader) never imports
    # main.py, so without this, logger.info() below would be entirely
    # silent — verified directly, not assumed.
    logging.basicConfig(level=logging.INFO)

    loader = CrimeDataLoader()
    logger.info("Loaded %d cities", len(loader))
    logger.info("Columns: %s", loader.df.columns.tolist())

    dc = loader.get_city("Delhi City")
    if not dc.empty:
        row = dc.iloc[0]
        logger.info("Delhi City murder=%s (quality=%s)", row["murder"], row["murder_quality"])
        logger.info("Delhi City rape=%s (quality=%s)", row["rape"], row["rape_quality"])
        assert row["murder"] == 506, f"Expected 506, got {row['murder']}"
        assert row["rape"] == 1088, f"Expected 1088, got {row['rape']}"
        logger.info("Delhi murder/rape assertions PASSED")

    bc = loader.get_city("Bengaluru")
    if not bc.empty:
        row = bc.iloc[0]
        logger.info("Bengaluru kidnapping=%s (quality=%s)", row["kidnapping"], row["kidnapping_quality"])
        assert row["kidnapping"] == 1203, f"Expected 1203, got {row['kidnapping']}"
        logger.info("Bengaluru kidnapping assertion PASSED")

    logger.info(
        "Maharashtra:\n%s",
        loader.get_state("Maharashtra")[["city", "crimes_per_lakh", "data_quality"]].to_string(index=False),
    )
    logger.info(
        "Top 5 by crimes_per_lakh:\n%s",
        loader.get_top_crimes(5)[["city", "crimes_per_lakh", "murder", "rape", "data_quality"]].to_string(index=False),
    )
    logger.info(
        "Top 5 women-risk cities:\n%s",
        loader.get_women_risk_cities(5)[["city", "rape", "kidnapping", "rape_quality", "kidnapping_quality"]].to_string(index=False),
    )
