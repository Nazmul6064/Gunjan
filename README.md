# Traffic Accident Hotspot Reporter

This repository contains a fully offline solution for analysing and
visualising traffic accident data.  The application reads a CSV file
containing accident records, cleans and validates the data, computes
key performance indicators, renders interactive charts and tables via
Streamlit, and allows the user to export cleaned and summarised
datasets for further review.

## Features

* **Data cleaning** – the `roadsense_data_cleaning_v1.py` module loads
  accident records from CSV, validates required columns, parses
  dates/times, fills or removes missing values, removes duplicates and
  flags severe accidents (major or critical).
* **KPI cards** – the dashboard reports total accidents, severe
  accidents, the peak accident hour and the top hotspot location.
* **Charts** – the dashboard displays accident frequency by hour,
  severity distribution by road type, a monthly trend line and
  accident counts by weather condition.
* **Hotspot ranking** – locations are ranked by accident count and
  severe accident count with ties broken alphabetically.
* **Filters** – date range, severity, road type, weather condition,
  zone and location filters help you explore subsets of the data.
* **CSV exports** – download the filtered and cleaned records, summary
  metrics and hotspot ranking as CSV files.
* **Test suite** – a small pytest suite verifies that data loading,
  cleaning and metric calculations behave as expected.

## Folder Structure

```
.
├── roadsense_data_cleaning_v1.py   # Data loading, validation and cleaning logic
├── roadsense_dashboard_v1.py       # Streamlit dashboard application
├── roadsense_tests_v1.py           # Unit tests using pytest
├── road_accident_records_2000_rows.csv  # Sample accident dataset (2000 rows)
├── dashboard_wireframe.png         # Wireframe used for layout inspiration
├── data_dictionary.md              # Field definitions for the accident CSV
├── expected_chart_specs.csv        # Expected views and filters
├── expected_kpi_summary.csv        # Example KPI summary values
├── hotspot_location_reference.csv  # Sample location reference data
├── report_rules.md                 # Rules for summarising the data
├── visual_output_requirements.md   # Description of required visuals
└── Traffic_Accident_Hotspot_PRD.docx.pdf  # Product requirements document
```

The script files and tests adhere to the naming convention
`roadsense_[name]_v1.*`.  Running the dashboard or tests does not
modify the sample data – exports are saved to new files as needed.

## Installation

1. **Install Python 3.10+** – ensure that Python version 3.10 or newer
   is installed on your system.
2. **Create a virtual environment** (optional but recommended):

   ```bash
   python -m venv venv
   source venv/bin/activate  # on Windows use venv\Scripts\activate
   ```

3. **Install dependencies** – the project relies only on a few
   publicly available packages.  Install them using pip:

   ```bash
   pip install pandas streamlit plotly pytest
   ```

## Running the Dashboard

To start the dashboard locally run:

```bash
streamlit run roadsense_dashboard_v1.py
```

On first launch the application loads the provided sample file
`road_accident_records_2000_rows.csv` from the repository.  You can
replace this file with another authorised CSV that follows the same
schema (see **Replacement CSVs** below) or use the file uploader in
the sidebar to analyse a different file.  All charts and KPIs update
dynamically based on your filter selections.

### Replacement CSVs

If you wish to analyse real accident data you must prepare a CSV file
with the same column names described in `data_dictionary.md`.  The
dashboard will load any authorised file that contains these fields.  To
use your own data:

1. Save your CSV locally.
2. Start the dashboard (`streamlit run roadsense_dashboard_v1.py`).
3. Use the **Upload CSV** control in the sidebar to select your file.
4. Ensure that the dataset is authorised and does not include
   personally identifiable information.

The application cleans and validates the uploaded file using the same
rules as the sample data.  If required columns are missing a clear
error message is shown.

## Exporting Results

The dashboard offers three download buttons beneath the hotspot ranking
table:

* **Cleaned Records CSV** – the filtered and cleaned accident records.
* **Summary Metrics CSV** – a table of the current KPI values (total
  accidents, severe accidents, peak hour, top hotspot, top road type,
  most common weather).
* **Hotspot Ranking CSV** – a ranking of locations by accident count
  and severe accident count.

All downloads respect the active filters so you can export subsets of
interest.

## Running Tests

To execute the unit tests run:

```bash
pytest roadsense_tests_v1.py
```

The tests cover loading, validation, date parsing and KPI
calculations.  They help ensure the integrity of the data cleaning
logic and provide assurance when modifying or extending the code.

## Offline Operation

This project is designed to run entirely offline.  It does not use
web scraping, paid APIs or cloud databases.  All data processing
happens on your local machine.

---

For further details on the project requirements please refer to the
`Traffic_Accident_Hotspot_PRD.docx.pdf` document and the accompanying
markdown files in the repository.
