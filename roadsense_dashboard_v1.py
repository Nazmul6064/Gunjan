"""
Streamlit Dashboard for Traffic Accident Hotspot Reporter (Version 1)
-------------------------------------------------------------------

This script implements an interactive dashboard using Streamlit to
visualise traffic accident data.  It relies on the data cleaning
functions defined in ``roadsense_data_cleaning_v1.py`` to load and
prepare the dataset.  Users may either analyse the provided sample
file or upload their own CSV as long as it follows the same schema.

The dashboard presents several key performance indicators (KPIs) and
charts including:

* Total accidents and severe accidents.
* The peak accident hour.
* The top hotspot location by accident count.
* Accident frequency by hour of day.
* Severity distribution by road type (stacked bar chart).
* Monthly accident trend (line chart).
* Accident counts by weather condition.
* A hotspot ranking table sorted by accident and severe accident
  counts.

Filters along the sidebar allow the user to restrict the analysis by
date range, severity, road type, weather condition, zone and specific
locations.  When filters narrow the dataset to zero rows an
informative message is displayed instead of empty charts.

The page also offers download buttons to save the cleaned records,
summary metrics and hotspot ranking as CSV files.  These downloads
reflect the currently selected filters, enabling convenient offline
analysis of subsets of the data.

This dashboard is fully offline and does not require any external
services.

Run the application with::

    streamlit run roadsense_dashboard_v1.py

"""

from __future__ import annotations

import io
import os
from datetime import date
from typing import Tuple, List

import pandas as pd
import plotly.express as px
import streamlit as st

from roadsense_data_cleaning_v1 import (
    load_data,
    validate_columns,
    clean_data,
    calculate_summary_metrics,
    generate_hotspot_ranking,
)


def get_default_csv_path() -> str:
    """Return the absolute path to the bundled sample CSV.

    The dashboard expects the sample file to reside in the same
    directory as this script or within the project root.  This helper
    resolves the file path relative to the location of this source file.
    """
    # If the file exists in the current working directory use that
    sample_name = "road_accident_records_2000_rows.csv"
    cwd_path = os.path.join(os.getcwd(), sample_name)
    if os.path.isfile(cwd_path):
        return cwd_path
    # Otherwise look relative to the script's directory
    script_dir = os.path.dirname(os.path.abspath(__file__))
    alt_path = os.path.join(script_dir, sample_name)
    return alt_path


def load_and_clean(file: str | io.BytesIO) -> pd.DataFrame:
    """Load and clean a CSV file or uploaded file like object.

    This wrapper handles both string file paths and file-like objects
    returned by Streamlit's file uploader.  It validates and cleans the
    dataset before returning it.

    Parameters
    ----------
    file : str or io.BytesIO
        Path to the CSV on disk or an in-memory buffer from a file
        upload.

    Returns
    -------
    pandas.DataFrame
        Cleaned accident records ready for analysis.

    Raises
    ------
    ValueError
        When required columns are missing.
    Exception
        Propagates parsing errors from pandas.
    """
    if isinstance(file, str):
        raw_df = load_data(file)
    else:
        raw_df = pd.read_csv(file)
    # Validate schema
    validate_columns(raw_df)
    cleaned_df = clean_data(raw_df)
    return cleaned_df


def apply_filters(
    df: pd.DataFrame,
    date_range: Tuple[date, date] | None,
    severities: List[str],
    road_types: List[str],
    weather_conditions: List[str],
    zones: List[str],
    locations: List[str],
) -> pd.DataFrame:
    """Filter the dataset according to the user's selections.

    Parameters
    ----------
    df : pandas.DataFrame
        Cleaned dataset.
    date_range : tuple of (start_date, end_date) or None
        Date range filter; when ``None`` no date filtering is applied.
    severities : list of str
        Selected severity values.  If empty the filter is ignored.
    road_types : list of str
        Selected road types.  If empty the filter is ignored.
    weather_conditions : list of str
        Selected weather conditions.  If empty the filter is ignored.
    zones : list of str
        Selected zones.  If empty the filter is ignored.
    locations : list of str
        Selected location names.  If empty the filter is ignored.

    Returns
    -------
    pandas.DataFrame
        Filtered DataFrame.  The returned DataFrame is a copy of the
        input and safe to further manipulate.
    """
    filtered = df.copy()
    # Date range filter
    if date_range is not None:
        start_date, end_date = date_range
        filtered = filtered[(filtered["accident_date"] >= pd.to_datetime(start_date)) & (filtered["accident_date"] <= pd.to_datetime(end_date))]
    # Severity filter
    if severities:
        filtered = filtered[filtered["severity"].isin(severities)]
    # Road type filter
    if road_types:
        filtered = filtered[filtered["road_type"].isin(road_types)]
    # Weather condition filter
    if weather_conditions:
        filtered = filtered[filtered["weather_condition"].isin(weather_conditions)]
    # Zone filter
    if zones:
        filtered = filtered[filtered["zone"].isin(zones)]
    # Location filter
    if locations:
        filtered = filtered[filtered["location_name"].isin(locations)]
    return filtered.reset_index(drop=True)


def build_dashboard():
    """Main function to construct the Streamlit dashboard."""
    st.set_page_config(
        page_title="Traffic Accident Hotspot Reporter",
        layout="wide",
    )
    st.title("Traffic Accident Hotspot Reporter")
    st.write(
        "This dashboard summarises traffic accident records to help identify high-risk times, locations and conditions. "
        "Use the filters in the sidebar to explore subsets of the data.")

    # Sidebar for file upload and filters
    with st.sidebar:
        st.header("Data Source")
        default_csv = get_default_csv_path()
        uploaded_file = st.file_uploader(
            "Upload CSV", type=["csv"], help="Upload a same-schema CSV to replace the sample data."
        )
        if uploaded_file is not None:
            data_file = uploaded_file
        else:
            data_file = default_csv

    # Attempt to load and clean the data
    try:
        df_clean = load_and_clean(data_file)
    except Exception as e:
        st.error(f"Failed to load the dataset: {e}")
        return

    # Build filter controls
    with st.sidebar:
        st.header("Filters")
        # Date range filter
        if not df_clean.empty:
            min_date = df_clean["accident_date"].min().date()
            max_date = df_clean["accident_date"].max().date()
            date_range = st.date_input(
                "Date range",
                value=(min_date, max_date),
                min_value=min_date,
                max_value=max_date,
            )
        else:
            date_range = None
        # Severity filter
        severity_options = sorted(df_clean["severity"].unique().tolist())
        selected_severities = st.multiselect(
            "Severity", options=severity_options, default=severity_options,
        )
        # Road type filter
        road_options = sorted(df_clean["road_type"].unique().tolist())
        selected_roads = st.multiselect(
            "Road type", options=road_options, default=road_options,
        )
        # Weather condition filter
        weather_options = sorted(df_clean["weather_condition"].unique().tolist())
        selected_weather = st.multiselect(
            "Weather condition", options=weather_options, default=weather_options,
        )
        # Zone filter
        zone_options = sorted(df_clean["zone"].unique().tolist())
        selected_zones = st.multiselect(
            "Zone", options=zone_options, default=zone_options,
        )
        # Location filter
        location_options = sorted(df_clean["location_name"].unique().tolist())
        selected_locations = st.multiselect(
            "Location", options=location_options, default=location_options,
        )

    # Apply filters
    filtered_df = apply_filters(
        df_clean,
        date_range if isinstance(date_range, tuple) and len(date_range) == 2 else None,
        selected_severities,
        selected_roads,
        selected_weather,
        selected_zones,
        selected_locations,
    )

    # Display message if no data after filtering
    if filtered_df.empty:
        st.warning("No records match the selected filters. Please adjust your selections.")
        return

    # Calculate summary metrics for the filtered dataset
    summary = calculate_summary_metrics(filtered_df)

    # KPI cards
    kpi1, kpi2, kpi3, kpi4 = st.columns(4)
    kpi1.metric(label="Total Accidents", value=summary["total_accidents"])
    kpi2.metric(label="Severe Accidents", value=summary["severe_accidents"])
    kpi3.metric(label="Peak Hour", value=summary["peak_hour"])
    kpi4.metric(label="Top Hotspot", value=summary["top_hotspot"])

    # Charts section
    # Accident frequency by hour
    hourly_counts = (
        filtered_df.groupby("hour_of_day")
        .size()
        .reindex(range(24), fill_value=0)
        .reset_index(name="accidents")
    )
    hourly_counts.rename(columns={"index": "hour_of_day"}, inplace=True)
    fig_hour = px.bar(
        hourly_counts,
        x="hour_of_day",
        y="accidents",
        labels={"hour_of_day": "Hour of Day", "accidents": "Accidents"},
        title="Accident Frequency by Hour",
    )
    fig_hour.update_xaxes(dtick=1)

    # Severity by road type (stacked bar)
    sev_by_road = (
        filtered_df.groupby(["road_type", "severity"])
        .size()
        .reset_index(name="count")
    )
    sev_order = ["minor", "moderate", "major", "critical"]
    fig_severity = px.bar(
        sev_by_road,
        x="road_type",
        y="count",
        color="severity",
        category_orders={"severity": sev_order},
        labels={"road_type": "Road Type", "count": "Accidents", "severity": "Severity"},
        title="Severity by Road Type",
    )
    fig_severity.update_layout(barmode="stack")

    # Monthly accident trend
    # Ensure months are sorted chronologically
    month_counts = (
        filtered_df.groupby("month")
        .size()
        .reset_index(name="accidents")
    )
    # Convert month string to date for sorting and plotting
    month_counts["month_date"] = pd.to_datetime(month_counts["month"] + "-01")
    month_counts = month_counts.sort_values("month_date")
    fig_month = px.line(
        month_counts,
        x="month_date",
        y="accidents",
        labels={"month_date": "Month", "accidents": "Accidents"},
        title="Monthly Accident Trend",
    )
    fig_month.update_xaxes(
        dtick="M1",
        tickformat="%Y-%m",
    )

    # Accident count by weather condition
    weather_counts = (
        filtered_df.groupby("weather_condition")
        .size()
        .reset_index(name="accidents")
        .sort_values("accidents", ascending=False)
    )
    fig_weather = px.bar(
        weather_counts,
        x="weather_condition",
        y="accidents",
        labels={"weather_condition": "Weather Condition", "accidents": "Accidents"},
        title="Accident Count by Weather Condition",
    )

    # Hotspot ranking
    ranking_df = generate_hotspot_ranking(filtered_df)
    # Only display top 10 to keep the table compact
    top_rank = ranking_df.head(10)

    # Layout charts using columns
    chart_col1, chart_col2 = st.columns(2)
    with chart_col1:
        st.plotly_chart(fig_hour, use_container_width=True)
        st.plotly_chart(fig_month, use_container_width=True)
    with chart_col2:
        st.plotly_chart(fig_severity, use_container_width=True)
        st.plotly_chart(fig_weather, use_container_width=True)

    # Hotspot ranking table
    st.subheader("Hotspot Ranking (Top 10)")
    st.dataframe(top_rank, use_container_width=True)

    # Download buttons
    st.subheader("Download Data")
    # Cleaned records CSV
    cleaned_csv = filtered_df.to_csv(index=False).encode("utf-8")
    st.download_button(
        label="Download Cleaned Records CSV",
        data=cleaned_csv,
        file_name="roadsense_cleaned_records_v1.csv",
        mime="text/csv",
    )
    # Summary metrics CSV
    summary_df = pd.DataFrame(list(summary.items()), columns=["metric", "value"])
    summary_csv = summary_df.to_csv(index=False).encode("utf-8")
    st.download_button(
        label="Download Summary Metrics CSV",
        data=summary_csv,
        file_name="roadsense_summary_metrics_v1.csv",
        mime="text/csv",
    )
    # Hotspot ranking CSV
    ranking_csv = ranking_df.to_csv(index=False).encode("utf-8")
    st.download_button(
        label="Download Hotspot Ranking CSV",
        data=ranking_csv,
        file_name="roadsense_hotspot_ranking_v1.csv",
        mime="text/csv",
    )


if __name__ == "__main__":
    build_dashboard()
