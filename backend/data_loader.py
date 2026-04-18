"""
data_loader.py — Real NCRB 2023 city-level crime data loader for SafeDistrict AI.

Crime-type breakdown (murder, rape, kidnapping, robbery, burglary, vehicle_theft)
is estimated by applying NCRB national average ratios to each city's real 2023
total IPC case count sourced from ipc_crimes_citywise_2023.xlsx.
"""

import numpy as np
import pandas as pd


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


def load_real_ncrb_data() -> pd.DataFrame:
    """Read and clean the raw NCRB 2023 city-wise IPC crimes Excel file.

    Returns
    -------
    pd.DataFrame
        Columns: city, cases_156_3, police_station_cases, total_ipc
        One row per city, 53 rows total.
    """
    df = pd.read_excel(
        "data/raw/ipc_crimes_citywise_2023.xlsx",
        skiprows=3,
        header=None,
    )
    df.columns = ["sl_no", "city", "cases_156_3", "police_station_cases", "total_ipc"]

    # Drop the last row (TOTAL CITIES aggregate)
    df = df.iloc[:-1].copy()

    df = df.drop(columns=["sl_no"])
    df["city"] = df["city"].str.strip()

    for col in ["cases_156_3", "police_station_cases", "total_ipc"]:
        df[col] = df[col].astype(int)

    return df.reset_index(drop=True)


def enrich_with_crime_breakdown(df: pd.DataFrame) -> pd.DataFrame:
    """Add estimated crime-type columns, state, population, year, and rate.

    Crime-type estimates are derived from NCRB national average ratios applied
    to each city's real total_ipc figure.

    Parameters
    ----------
    df : pd.DataFrame
        Clean DataFrame produced by load_real_ncrb_data().

    Returns
    -------
    pd.DataFrame
        Enriched DataFrame with columns: city, state, year, murder, rape,
        kidnapping, robbery, burglary, vehicle_theft, total_ipc, population,
        crimes_per_lakh, cases_156_3, police_station_cases.
    """
    df = df.copy()

    df["murder"]        = (df["total_ipc"] * 0.008).round().astype(int)
    df["rape"]          = (df["total_ipc"] * 0.021).round().astype(int)
    df["kidnapping"]    = (df["total_ipc"] * 0.034).round().astype(int)
    df["robbery"]       = (df["total_ipc"] * 0.012).round().astype(int)
    df["burglary"]      = (df["total_ipc"] * 0.085).round().astype(int)
    df["vehicle_theft"] = (df["total_ipc"] * 0.142).round().astype(int)

    df["state"] = df["city"].map(_CITY_STATE).fillna("Other")
    df["population"] = df["city"].map(_CITY_POPULATION).fillna(500000).astype(int)
    df["year"] = 2023
    df["crimes_per_lakh"] = ((df["total_ipc"] / df["population"]) * 100000).round(2)

    return df[
        [
            "city", "state", "year",
            "murder", "rape", "kidnapping", "robbery", "burglary", "vehicle_theft",
            "total_ipc", "population", "crimes_per_lakh",
            "cases_156_3", "police_station_cases",
        ]
    ]


def load_crime_data() -> pd.DataFrame:
    """Load, enrich, and return the full NCRB 2023 city-level crime DataFrame.

    Returns
    -------
    pd.DataFrame
        53-row DataFrame ready for RAG ingestion and anomaly detection.
    """
    df = load_real_ncrb_data()
    df = enrich_with_crime_breakdown(df)
    return df


class CrimeDataLoader:
    """High-level query interface over the real NCRB 2023 city crime dataset.

    Attributes
    ----------
    df : pd.DataFrame
        Enriched 53-city DataFrame produced by load_crime_data().
    """

    def __init__(self) -> None:
        """Load and cache the full crime DataFrame on construction."""
        self.df: pd.DataFrame = load_crime_data()

    def get_state(self, state_name: str) -> pd.DataFrame:
        """Return all cities in the given state (case-insensitive).

        Parameters
        ----------
        state_name : str
            E.g. ``"Maharashtra"``.

        Returns
        -------
        pd.DataFrame
            Subset of self.df for the requested state.
        """
        mask = self.df["state"].str.lower() == state_name.lower()
        return self.df[mask].reset_index(drop=True)

    def get_city(self, city_name: str) -> pd.DataFrame:
        """Return the row(s) for the given city (case-insensitive).

        Parameters
        ----------
        city_name : str
            E.g. ``"Pune"``.

        Returns
        -------
        pd.DataFrame
            Matching row(s) from self.df.
        """
        mask = self.df["city"].str.lower() == city_name.lower()
        return self.df[mask].reset_index(drop=True)

    def get_top_crimes(self, n: int = 5) -> pd.DataFrame:
        """Return the n cities with the highest crimes_per_lakh rate.

        Parameters
        ----------
        n : int, optional
            Number of cities to return (default 5).

        Returns
        -------
        pd.DataFrame
            Top-n rows sorted descending by crimes_per_lakh.
        """
        return self.df.nlargest(n, "crimes_per_lakh").reset_index(drop=True)

    def get_women_risk_cities(self, n: int = 5) -> pd.DataFrame:
        """Return the n cities with the highest combined rape + kidnapping count.

        Parameters
        ----------
        n : int, optional
            Number of cities to return (default 5).

        Returns
        -------
        pd.DataFrame
            Top-n rows sorted descending by rape + kidnapping total.
        """
        df = self.df.copy()
        df["women_risk"] = df["rape"] + df["kidnapping"]
        return (
            df.nlargest(n, "women_risk")
            .drop(columns=["women_risk"])
            .reset_index(drop=True)
        )

    def __len__(self) -> int:
        """Return the number of cities in the dataset."""
        return len(self.df)

    def __repr__(self) -> str:
        """Return a concise debug summary of the loader."""
        states = self.df["state"].nunique()
        return (
            f"CrimeDataLoader("
            f"cities={len(self)}, "
            f"states={states}, "
            f"year=2023, "
            f"source=NCRB ipc_crimes_citywise_2023.xlsx)"
        )


# ---------------------------------------------------------------------------
# Smoke-test entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    loader = CrimeDataLoader()
    print(f"Loaded {len(loader)} real NCRB cities")
    print(loader.df.columns.tolist())

    print("\n--- Maharashtra ---")
    print(loader.get_state("Maharashtra").to_string(index=False))

    print("\n--- Top 5 cities by crimes_per_lakh ---")
    print(loader.get_top_crimes(5).to_string(index=False))

    print("\n--- Top 5 cities by women risk (rape + kidnapping) ---")
    print(loader.get_women_risk_cities(5).to_string(index=False))
