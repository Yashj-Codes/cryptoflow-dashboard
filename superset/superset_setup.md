# Apache Superset Setup for CryptoFlow

This guide connects Apache Superset to the local `cryptoflow.db` SQLite database created by `python pipeline/api_ingest.py`.

## Option 1: Install Superset with pip

```bash
python -m venv superset-venv
source superset-venv/bin/activate
pip install apache-superset
superset db upgrade
export FLASK_APP=superset
superset fab create-admin
superset init
superset run -p 8088 --with-threads --reload --debugger
```

Open `http://localhost:8088` and sign in with the admin account created during setup.

## Option 2: Run Superset with Docker

```bash
git clone https://github.com/apache/superset.git
cd superset
docker compose -f docker-compose-non-dev.yml up
```

When Docker is running, open `http://localhost:8088`. Mount the CryptoFlow project folder into the Superset container if you want SQLite access from Docker.

## Prepare the CryptoFlow Database

From this project folder, run:

```bash
pip install -r requirements.txt
python data/generate_sample_data.py
python pipeline/api_ingest.py
```

The SQLite file will be created at:

```text
cryptoflow.db
```

## Connect Superset to SQLite

1. In Superset, go to **Settings > Database Connections**.
2. Click **+ Database**.
3. Choose **SQLite**.
4. Use the SQLAlchemy URI below, replacing the path with your absolute project path:

```text
sqlite:////absolute/path/to/cryptoflow-dashboard/cryptoflow.db
```

5. Test the connection and save it as `CryptoFlow SQLite`.

Superset reads database tables directly. The `market_data` table is available after API ingestion. To use `funnel_events.csv` in Superset, import it as a dataset or load it into SQLite with your preferred SQLite client.

## Create Chart 1: KYC Funnel Bar Chart

1. Create a dataset from the `funnel_events` table or imported CSV.
2. Open **Charts > + Chart**.
3. Select the funnel dataset.
4. Choose **Bar Chart**.
5. Configure:
   - Dimension: `step_name`
   - Metric: `COUNT_DISTINCT(user_id)`
   - Sort: `step_order ASC`
   - Time range: no filter, or last 90 days
6. Save as `KYC Funnel Bar Chart`.

Use the SQL from `sql/kyc_funnel.sql` as a virtual dataset when you want drop rate and cumulative signup percentage directly in Superset.

## Create Chart 2: Market Data Time Series

1. Create a dataset from `market_data`.
2. Create a **Time-series Line Chart**.
3. Configure:
   - Time column: `timestamp`
   - Metric: `AVG(current_price)` or `SUM(total_volume)`
   - Group by: `symbol`
   - Time grain: minute or hour
4. Save as `Market Data Time Series`.

## Create Chart 3: Cohort Heatmap

1. Use `sql/cohort_retention.sql` as a SQL Lab query.
2. Save the query as a virtual dataset named `cohort_retention`.
3. Create a **Heatmap** chart.
4. Configure:
   - X-axis: retention week fields such as `week_1_retention_pct`
   - Y-axis: `cohort_week`
   - Metric: retention percentage
5. Save as `Cohort Retention Heatmap`.

## Build and Export the Superset Dashboard

1. Go to **Dashboards > + Dashboard**.
2. Name it `CryptoFlow Analytics Dashboard`.
3. Add the three charts:
   - `KYC Funnel Bar Chart`
   - `Market Data Time Series`
   - `Cohort Retention Heatmap`
4. Arrange charts to match the Streamlit tabs.
5. Click the dashboard menu and choose **Export**.
6. Save the generated JSON or ZIP export as your Superset dashboard backup.

The exported Superset artifact can be imported into another Superset instance from **Settings > Import Dashboards**.
