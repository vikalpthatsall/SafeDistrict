"""
ncrb_2023_verified.py — Verified NCRB 2023 crime statistics for Indian metro cities.

Source: NCRB Crime in India 2023
https://data.opencity.in/dataset/crime-in-india-2023
"""

# Verified total IPC crime rate per lakh population — 19 major metros (NCRB 2023 Table 17A)
NCRB_2023_CRIME_RATE_PER_LAKH = {
    "Delhi":       1832.6,
    "Jaipur":       916.7,
    "Indore":       767.7,
    "Kochi":        626.7,
    "Patna":        611.7,
    "Lucknow":      521.0,
    "Nagpur":       516.0,
    "Ghaziabad":    418.0,
    "Kanpur":       401.4,
    "Kozhikode":    397.5,
    "Mumbai":       367.3,
    "Ahmedabad":    360.1,
    "Bengaluru":    337.3,
    "Hyderabad":    266.7,
    "Pune":         219.3,
    "Surat":        215.3,
    "Coimbatore":   211.2,
    "Chennai":      211.2,
    "Kolkata":       78.2,
}

# Verified murder rate per lakh population — 9 cities (NCRB 2023)
NCRB_2023_MURDER_RATE_PER_LAKH = {
    "Patna":      5.2,
    "Lucknow":    4.5,
    "Jaipur":     4.3,
    "Indore":     3.3,
    "Ghaziabad":  3.1,
    "Kochi":      0.8,
    "Mumbai":     0.7,
    "Kozhikode":  0.3,
    "Kolkata":    0.2,
}

# Verified absolute murder counts (NCRB 2023 Table 1A)
NCRB_2023_MURDERS = {
    "Delhi City": 506,
    "Bengaluru":  206,
}

# Verified absolute rape case counts (NCRB 2023)
NCRB_2023_RAPE = {
    "Delhi City": 1088,
    "Jaipur":      573,
    "Mumbai":      196,
}

# Verified absolute kidnapping counts (NCRB 2023)
NCRB_2023_KIDNAPPING = {
    "Bengaluru": 1203,
}

# State-level crime-type ratios (fraction of total IPC), differentiated by state profile
# Based on NCRB 2023 state-wise data; NOT a single national ratio applied everywhere
NCRB_2023_STATE_RATIOS = {
    "Delhi": {
        "murder":        0.0025,
        "rape":          0.0054,
        "kidnapping":    0.0450,
        "robbery":       0.0180,
        "burglary":      0.0600,
        "vehicle_theft": 0.1800,
    },
    "Rajasthan": {
        "murder":        0.0070,
        "rape":          0.0310,
        "kidnapping":    0.0300,
        "robbery":       0.0100,
        "burglary":      0.0900,
        "vehicle_theft": 0.1400,
    },
    "Madhya Pradesh": {
        "murder":        0.0080,
        "rape":          0.0200,
        "kidnapping":    0.0350,
        "robbery":       0.0120,
        "burglary":      0.0850,
        "vehicle_theft": 0.1400,
    },
    "Kerala": {
        "murder":        0.0030,
        "rape":          0.0100,
        "kidnapping":    0.0200,
        "robbery":       0.0080,
        "burglary":      0.0700,
        "vehicle_theft": 0.1200,
    },
    "Bihar": {
        "murder":        0.0150,
        "rape":          0.0200,
        "kidnapping":    0.0500,
        "robbery":       0.0150,
        "burglary":      0.0700,
        "vehicle_theft": 0.1000,
    },
    "Uttar Pradesh": {
        "murder":        0.0100,
        "rape":          0.0180,
        "kidnapping":    0.0450,
        "robbery":       0.0150,
        "burglary":      0.0800,
        "vehicle_theft": 0.1300,
    },
    "Maharashtra": {
        "murder":        0.0050,
        "rape":          0.0120,
        "kidnapping":    0.0250,
        "robbery":       0.0100,
        "burglary":      0.0800,
        "vehicle_theft": 0.1500,
    },
    "Karnataka": {
        "murder":        0.0072,
        "rape":          0.0150,
        "kidnapping":    0.0423,
        "robbery":       0.0120,
        "burglary":      0.0900,
        "vehicle_theft": 0.1600,
    },
    "Telangana": {
        "murder":        0.0050,
        "rape":          0.0120,
        "kidnapping":    0.0250,
        "robbery":       0.0100,
        "burglary":      0.0750,
        "vehicle_theft": 0.1400,
    },
    "Gujarat": {
        "murder":        0.0040,
        "rape":          0.0120,
        "kidnapping":    0.0250,
        "robbery":       0.0080,
        "burglary":      0.0750,
        "vehicle_theft": 0.1300,
    },
    "West Bengal": {
        "murder":        0.0026,
        "rape":          0.0150,
        "kidnapping":    0.0300,
        "robbery":       0.0100,
        "burglary":      0.0800,
        "vehicle_theft": 0.1200,
    },
    "Tamil Nadu": {
        "murder":        0.0050,
        "rape":          0.0100,
        "kidnapping":    0.0200,
        "robbery":       0.0100,
        "burglary":      0.0900,
        "vehicle_theft": 0.1500,
    },
    "Haryana": {
        "murder":        0.0100,
        "rape":          0.0180,
        "kidnapping":    0.0400,
        "robbery":       0.0130,
        "burglary":      0.0850,
        "vehicle_theft": 0.1300,
    },
    "Punjab": {
        "murder":        0.0080,
        "rape":          0.0150,
        "kidnapping":    0.0250,
        "robbery":       0.0100,
        "burglary":      0.0800,
        "vehicle_theft": 0.1350,
    },
    "Jharkhand": {
        "murder":        0.0120,
        "rape":          0.0200,
        "kidnapping":    0.0400,
        "robbery":       0.0150,
        "burglary":      0.0750,
        "vehicle_theft": 0.1200,
    },
    "Chhattisgarh": {
        "murder":        0.0090,
        "rape":          0.0180,
        "kidnapping":    0.0300,
        "robbery":       0.0130,
        "burglary":      0.0800,
        "vehicle_theft": 0.1300,
    },
    "Andhra Pradesh": {
        "murder":        0.0060,
        "rape":          0.0140,
        "kidnapping":    0.0250,
        "robbery":       0.0100,
        "burglary":      0.0800,
        "vehicle_theft": 0.1450,
    },
    "Jammu & Kashmir": {
        "murder":        0.0070,
        "rape":          0.0120,
        "kidnapping":    0.0350,
        "robbery":       0.0100,
        "burglary":      0.0700,
        "vehicle_theft": 0.1000,
    },
    "Chandigarh": {
        "murder":        0.0040,
        "rape":          0.0130,
        "kidnapping":    0.0250,
        "robbery":       0.0100,
        "burglary":      0.0750,
        "vehicle_theft": 0.1300,
    },
}

# National average ratios — fallback only when state not in NCRB_2023_STATE_RATIOS
NCRB_2023_NATIONAL_RATIOS = {
    "murder":        0.0080,
    "rape":          0.0210,
    "kidnapping":    0.0340,
    "robbery":       0.0120,
    "burglary":      0.0850,
    "vehicle_theft": 0.1420,
}

# 13 verified key findings from NCRB Crime in India 2023
NCRB_2023_KEY_FINDINGS = [
    "Delhi has the highest crime rate among Indian metro cities at 1,832.6 per lakh population (NCRB 2023).",
    "Delhi City reported 506 murders in 2023 — the highest absolute murder count among metros (NCRB 2023).",
    "Delhi City reported 1,088 rape cases in 2023 — the highest among all Indian metro cities (NCRB 2023).",
    "Jaipur reported 573 rape cases in 2023 — second highest among metros despite a smaller population than Mumbai.",
    "Mumbai reported 196 rape cases in 2023, relatively low for India's most populous metro (NCRB 2023).",
    "Bengaluru reported 1,203 kidnapping cases in 2023 — the highest among all Indian metro cities (NCRB 2023).",
    "Bengaluru reported 206 murders in 2023 (NCRB 2023).",
    "Kolkata has the lowest crime rate among the 19 major metros at just 78.2 per lakh population.",
    "Pune is among the safer large cities at 219.3 crimes per lakh — significantly below the national metro average.",
    "Patna has the highest murder rate per lakh population (5.2) among cities with NCRB-verified murder rate data.",
    "Kerala cities (Kochi at 626.7, Kozhikode at 397.5 per lakh) show above-average overall crime rates but have among the lowest murder rates nationally.",
    "Southern cities Coimbatore and Chennai both report crime rates of 211.2 per lakh — well below the high-crime northern metros.",
    "The crime rate gap between the safest metro (Kolkata: 78.2) and most dangerous (Delhi: 1,832.6) is over 23-fold.",
]

DATA_SOURCES = {
    "primary": {
        "name": "NCRB Crime in India 2023",
        "url": "https://data.opencity.in/dataset/crime-in-india-2023",
        "publisher": "National Crime Records Bureau, Ministry of Home Affairs, India",
        "year": 2023,
        "tables_used": [
            "Table 17A - IPC Crimes in Cities (City-wise)",
            "Table 1 - Total Cognizable Crimes",
            "Table 1A - City-wise Crime Rates",
        ],
    },
    "population": {
        "name": "Census of India 2011 + projections",
        "note": "City populations projected to 2023 using decadal growth rates",
    },
    "access_date": "2024",
    "license": "Government of India Open Data License",
}
