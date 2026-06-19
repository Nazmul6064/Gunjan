"""
Test suite for the RoadSense accident reporting project (version 1).

This module contains a series of unit tests exercising the data
cleaning and KPI calculation functions defined in
``roadsense_data_cleaning_v1.py``.  The tests verify that the
following behaviours are implemented correctly:

* Loading data from the sample CSV produces a DataFrame with all
  required columns.
* Missing required columns result in a meaningful error.
* Date parsing converts the ``accident_date`` column to a datetime
  dtype and invalid dates are removed.
* KPI calculations return expected values for the supplied sample
  dataset by comparing the implementation to a manual calculation.

Run this test suite with pytest::

    pytest roadsense_tests_v1.py

"""

from __future__ import annotations

import os
import pandas as pd
import numpy as np

import pytest

from roadsense_data_cleaning_v1 import (
    load_data,
    validate_columns,
    clean_data,
    calculate_summary_metrics,
    generate_hotspot_ranking,
    REQUIRED_COLUMNS,
)


SAMPLE_CSV = os.path.join(os.path.dirname(__file__), "road_accident_records_2000_rows.csv")


def test_load_data_and_validate_columns(tmp_path):
    """Ensure the loader returns a DataFrame with required columns."""
    # Copy sample file into temporary directory to avoid modification
    sample_copy = tmp_path / "records.csv"
    df_original = load_data(SAMPLE_CSV)
    df_original.to_csv(sample_copy, index=False)
    # Load via loader
    df_loaded = load_data(str(sample_copy))
    # Validate required columns present
    validate_columns(df_loaded)
    for col in REQUIRED_COLUMNS:
        assert col in df_loaded.columns


def test_missing_required_columns_raises_error():
    """Ensure validate_columns raises a ValueError when fields are missing."""
    df = pd.DataFrame({"accident_id": ["A1"], "accident_date": ["2026-01-01"]})
    # severity is missing; expect error
    with pytest.raises(ValueError):
        validate_columns(df)


def test_date_parsing_and_cleaning():
    """Verify that the cleaning function parses dates and drops invalid rows."""
    df = pd.DataFrame({
        "accident_id": ["A1", "A2", "A3"],
        "accident_date": ["2026-01-01", "not-a-date", "2026-03-03"],
        "accident_time": ["08:00", "09:15", "17:30"],
        "hour_of_day": [8, 9, 17],
        "month": ["2026-01", "2026-02", "2026-03"],
        "location_name": ["Loc1", "Loc2", "Loc3"],
        "zone": ["Z1", "Z2", "Z3"],
        "road_type": ["highway", "local_road", "arterial"],
        "severity": ["minor", "major", "critical"],
        "weather_condition": ["clear", "rain", "fog"],
    })
    cleaned = clean_data(df)
    # Row with invalid date should be dropped
    assert len(cleaned) == 2
    # accident_date should be datetime
    assert pd.api.types.is_datetime64_any_dtype(cleaned["accident_date"])


def test_kpi_calculations_match_manual():
    """Compare summary metrics from implementation against manual calculation."""
    df_raw = load_data(SAMPLE_CSV)
    validate_columns(df_raw)
    df = clean_data(df_raw)
    summary = calculate_summary_metrics(df)
    # Manual calculations
    manual_total = len(df)
    manual_severe = int(df["is_severe"].sum())
    hour_counts = df.groupby("hour_of_day").size()
    manual_peak_hour = hour_counts.idxmax()
    manual_peak_count = int(hour_counts.max())
    manual_peak_str = f"{manual_peak_hour:02d}:00 with {manual_peak_count} records"
    hotspot_counts = df.groupby("location_name").size()
    severe_counts = df.groupby("location_name")["is_severe"].sum()
    hotspot_df = pd.DataFrame({
        "accidents": hotspot_counts,
        "severe": severe_counts,
    })
    hotspot_df = hotspot_df.sort_values(
        by=["accidents", "severe", "location_name"],
        ascending=[False, False, True],
    )
    top_loc = hotspot_df.iloc[0]
    manual_top_hotspot = f"{top_loc.name} with {int(top_loc['accidents'])} records"
    road_counts = df["road_type"].value_counts()
    manual_top_road = road_counts.idxmax()
    weather_counts = df["weather_condition"].value_counts()
    manual_top_weather = weather_counts.idxmax()
    # Assert equality
    assert summary["total_accidents"] == manual_total
    assert summary["severe_accidents"] == manual_severe
    assert summary["peak_hour"] == manual_peak_str
    assert summary["top_hotspot"] == manual_top_hotspot
    assert summary["top_road_type"] == manual_top_road
    assert summary["most_common_weather"] == manual_top_weather
