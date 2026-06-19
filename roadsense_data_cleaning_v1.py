"""
RoadSense Data Cleaning Module (Version 1)
----------------------------------------

This module provides reusable functions for loading, validating and
cleaning road accident records contained within a CSV file.  It also
supplies helper routines for computing summary metrics and hotspot
rankings from a cleaned dataset.  The functions defined here are
intended for use both by the Streamlit dashboard and in offline
analysis scripts or tests.  They do not make any network calls and
operate entirely on local data.

Key responsibilities of this module:

* Load accident records from a CSV file using pandas.
* Validate that all required columns are present before analysis.
* Parse accident dates to pandas `datetime64` dtype.
* Handle missing values by filling non‐critical columns with
  placeholder strings and dropping rows with missing critical data.
* Remove duplicate records based on the unique accident identifier.
* Provide functions to calculate high level summary statistics such as
  total accidents, number of severe accidents, peak accident hour,
  most dangerous hotspot, top road type and most common weather
  condition.
* Produce a hotspot ranking table sorted by accident count and severe
  accident count.

The cleaning rules implemented here follow the supplied product
requirements document and report rules.  Any authorised CSV file
following the same schema may be passed through these functions.

Example usage::

    from roadsense_data_cleaning_v1 import (
        load_data, validate_columns, clean_data,
        calculate_summary_metrics, generate_hotspot_ranking
    )

    raw_df = load_data('road_accident_records_2000_rows.csv')
    validate_columns(raw_df)
    cleaned_df = clean_data(raw_df)
    summary = calculate_summary_metrics(cleaned_df)
    ranking = generate_hotspot_ranking(cleaned_df)
    cleaned_df.to_csv('roadsense_cleaned_records_v1.csv', index=False)
    summary_df = pd.DataFrame(list(summary.items()), columns=['metric', 'value'])
    summary_df.to_csv('roadsense_summary_metrics_v1.csv', index=False)
    ranking.to_csv('roadsense_hotspot_ranking_v1.csv', index=False)

"""

from __future__ import annotations

import os
from typing import Iterable, Dict, List, Tuple

import pandas as pd
import numpy as np


# ---------------------------------------------------------------------------
# Constants
#
# List of columns that must exist in the accident record CSV for the
# subsequent analysis to function correctly.  If any of these fields are
# missing the caller should be notified immediately via an exception.
REQUIRED_COLUMNS: Tuple[str, ...] = (
    "accident_id",
    "accident_date",
    "accident_time",
    "hour_of_day",
    "month",
    "location_name",
    "zone",
    "road_type",
    "severity",
    "weather_condition",
)


def load_data(file_path: str) -> pd.DataFrame:
    """Load accident records from a CSV file.

    Parameters
    ----------
    file_path : str
        Absolute or relative path to the CSV file containing accident
        records.

    Returns
    -------
    pandas.DataFrame
        DataFrame containing all columns from the input file.  Data is
        loaded with `dtype` inference; fields such as dates and times
        remain string typed until cleaned.

    Raises
    ------
    FileNotFoundError
        If the provided `file_path` does not exist on disk.
    pd.errors.EmptyDataError
        If the CSV file is empty.
    pd.errors.ParserError
        If pandas cannot parse the CSV file.
    """
    if not os.path.isfile(file_path):
        raise FileNotFoundError(f"CSV file not found: {file_path}")
    return pd.read_csv(file_path)


def validate_columns(df: pd.DataFrame, required_columns: Iterable[str] = REQUIRED_COLUMNS) -> None:
    """Verify that a DataFrame contains all required columns.

    Parameters
    ----------
    df : pandas.DataFrame
        The DataFrame to validate.
    required_columns : Iterable[str], optional
        An iterable of column names that must be present in the
        DataFrame.  Defaults to :data:`REQUIRED_COLUMNS`.

    Raises
    ------
    ValueError
        If one or more required columns are missing.
    """
    missing = [col for col in required_columns if col not in df.columns]
    if missing:
        raise ValueError(
            f"The following required columns are missing from the dataset: {', '.join(missing)}"
        )


def clean_data(df: pd.DataFrame) -> pd.DataFrame:
    """Clean raw accident data according to project rules.

    This function performs several cleaning steps:

    * Converts the `accident_date` column to datetime.  Rows with
      unparsable dates are dropped.
    * Computes numeric hours from `accident_time` if `hour_of_day` is
      missing or non-integer.  If `hour_of_day` exists and is numeric it
      is left intact.  In either case the resulting values are coerced
      to integers in the range [0, 23].  Rows with invalid times are
      dropped.
    * Fills missing categorical values (`weather_condition`,
      `lighting_condition`, `reported_cause`, `road_type`, `severity`,
      `location_name`, `zone`) with the placeholder ``"Unknown"``.
    * Drops rows that still contain missing values in any of the
      required columns after filling.
    * Removes duplicate records based on the ``accident_id`` column,
      keeping the first occurrence.

    Parameters
    ----------
    df : pandas.DataFrame
        Raw accident data loaded from CSV.

    Returns
    -------
    pandas.DataFrame
        A cleaned DataFrame ready for analysis.  The returned object
        includes all original columns plus a boolean ``is_severe``
        indicating whether each accident is classified as severe (major
        or critical).
    """
    df = df.copy()

    # Convert accident_date to datetime; drop rows with invalid dates
    df["accident_date"] = pd.to_datetime(df["accident_date"], errors="coerce")
    # Compute month string (YYYY-MM) if not already present; use period
    if "month" not in df.columns:
        df["month"] = df["accident_date"].dt.to_period("M").astype(str)
    # Drop rows with NaT dates
    df = df.dropna(subset=["accident_date"])

    # Ensure hour_of_day is an integer 0-23.  If non-numeric values
    # appear or the column is missing, derive from accident_time.
    if "hour_of_day" not in df.columns or not pd.api.types.is_numeric_dtype(df["hour_of_day"]):
        # Derive hour from accident_time strings (format HH:MM)
        def parse_hour(value: str) -> np.float64:
            try:
                if isinstance(value, (int, float)):
                    return int(value)
                return int(str(value).split(":")[0])
            except Exception:
                return np.nan
        df["hour_of_day"] = df["accident_time"].apply(parse_hour)
    # Coerce to numeric and fill invalid values with NaN
    df["hour_of_day"] = pd.to_numeric(df["hour_of_day"], errors="coerce").astype(float)
    df = df[(df["hour_of_day"] >= 0) & (df["hour_of_day"] <= 23)]
    df["hour_of_day"] = df["hour_of_day"].astype(int)

    # Fill missing categorical values for non-critical columns
    categorical_fields = [
        "weather_condition",
        "lighting_condition",
        "reported_cause",
        "road_type",
        "severity",
        "location_name",
        "zone",
    ]
    for col in categorical_fields:
        if col not in df.columns:
            # Create the column if it doesn't exist to ensure consistency
            df[col] = "Unknown"
        else:
            df[col] = df[col].fillna("Unknown")

    # Drop any remaining rows with missing required fields
    df = df.dropna(subset=list(REQUIRED_COLUMNS))

    # Remove duplicate accident_id rows
    df = df.drop_duplicates(subset="accident_id", keep="first")

    # Compute is_severe boolean: major or critical
    df["is_severe"] = df["severity"].str.lower().isin(["major", "critical"])

    return df.reset_index(drop=True)


def calculate_summary_metrics(df: pd.DataFrame) -> Dict[str, str]:
    """Calculate high level KPI metrics from a cleaned dataset.

    This helper computes metrics required by the dashboard and report
    rules.  It expects the DataFrame to already be cleaned (for
    example, using :func:`clean_data`).

    Parameters
    ----------
    df : pandas.DataFrame
        Cleaned accident records.  Must include ``hour_of_day``,
        ``location_name``, ``road_type``, ``weather_condition`` and
        ``is_severe`` fields.

    Returns
    -------
    dict
        A mapping where keys correspond to metric names and values are
        human readable strings or numbers.  Metrics include:

        - ``total_accidents``: total number of accident records.
        - ``severe_accidents``: count of records where ``is_severe`` is
          True.
        - ``peak_hour``: string describing the hour with the highest
          number of accidents (e.g. ``"17:00 with 149 records"``).
        - ``top_hotspot``: string describing the location with the
          highest accident count, including the record count.
        - ``top_road_type``: most common road type.
        - ``most_common_weather``: most common weather condition.
    """
    if df.empty:
        # Provide sensible defaults when no data is available.
        return {
            "total_accidents": 0,
            "severe_accidents": 0,
            "peak_hour": "N/A",
            "top_hotspot": "N/A",
            "top_road_type": "N/A",
            "most_common_weather": "N/A",
        }

    # Total number of records
    total_accidents = int(len(df))

    # Severe accidents count
    severe_accidents = int(df["is_severe"].sum())

    # Peak hour: find hour_of_day with max accidents
    hour_counts = df.groupby("hour_of_day").size()
    peak_hour_val = hour_counts.idxmax()
    peak_hour_count = int(hour_counts.max())
    peak_hour_formatted = f"{peak_hour_val:02d}:00 with {peak_hour_count} records"

    # Top hotspot: location with highest accident count; tie break by severe accidents then name
    hotspot_counts = df.groupby("location_name").size()
    severe_counts = df.groupby("location_name")["is_severe"].sum()
    hotspot_df = pd.DataFrame({
        "accidents": hotspot_counts,
        "severe_accidents": severe_counts,
    })
    hotspot_df = hotspot_df.sort_values(
        by=["accidents", "severe_accidents", "location_name"],
        ascending=[False, False, True],
    )
    top_hotspot_row = hotspot_df.iloc[0]
    top_hotspot_name = top_hotspot_row.name
    top_hotspot_count = int(top_hotspot_row["accidents"])
    top_hotspot_formatted = f"{top_hotspot_name} with {top_hotspot_count} records"

    # Top road type
    road_counts = df["road_type"].value_counts()
    top_road_type = road_counts.idxmax() if not road_counts.empty else "N/A"

    # Most common weather
    weather_counts = df["weather_condition"].value_counts()
    most_common_weather = weather_counts.idxmax() if not weather_counts.empty else "N/A"

    return {
        "total_accidents": total_accidents,
        "severe_accidents": severe_accidents,
        "peak_hour": peak_hour_formatted,
        "top_hotspot": top_hotspot_formatted,
        "top_road_type": top_road_type,
        "most_common_weather": most_common_weather,
    }


def generate_hotspot_ranking(df: pd.DataFrame) -> pd.DataFrame:
    """Generate a ranking of locations by accident and severe accident count.

    This function groups the dataset by ``location_name`` and computes
    total accident counts and the number of severe accidents for each
    location.  The resulting DataFrame is sorted in descending order of
    accident count and severe accident count.  Ties on both counts are
    resolved alphabetically by location name.

    Parameters
    ----------
    df : pandas.DataFrame
        Cleaned accident records containing ``location_name`` and
        ``is_severe`` fields.

    Returns
    -------
    pandas.DataFrame
        A DataFrame with the columns ``location_name``, ``accidents``
        and ``severe_accidents``, sorted by the ranking criteria.
    """
    if df.empty:
        return pd.DataFrame(columns=["location_name", "accidents", "severe_accidents"])  # empty

    accident_counts = df.groupby("location_name").size()
    severe_counts = df.groupby("location_name")["is_severe"].sum()
    ranking = pd.DataFrame({
        "location_name": accident_counts.index,
        "accidents": accident_counts.values,
        "severe_accidents": severe_counts.loc[accident_counts.index].values,
    })
    ranking = ranking.sort_values(
        by=["accidents", "severe_accidents", "location_name"],
        ascending=[False, False, True],
    ).reset_index(drop=True)
    return ranking
