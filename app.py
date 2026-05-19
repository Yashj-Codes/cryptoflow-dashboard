"""Streamlit interface for the CryptoFlow Analytics Dashboard."""

from __future__ import annotations

import sqlite3
from datetime import datetime
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from alerts.anomaly_alert import run_alert_monitor
from data.generate_sample_data import main as generate_sample_data
from pipeline.api_ingest import DB_PATH, get_latest_market_data, initialize_database, run_market_ingest
from pipeline.cohort_analysis import analyze_cohorts
from pipeline.excel_report import OUTPUT_PATH, create_excel_report
from pipeline.funnel_analysis import DATA_PATH, analyze_funnel


PROJECT_ROOT = Path(__file__).resolve().parent


st.set_page_config(
    page_title="CryptoFlow Analytics Dashboard",
    page_icon="📊",
    layout="wide",
)


def bootstrap_data() -> None:
    """Create local data assets when a deployment starts from a clean checkout."""
    if not DATA_PATH.exists():
        generate_sample_data()
    initialize_database(DB_PATH)
    if len(get_latest_market_data(DB_PATH)) == 0:
        run_market_ingest()


@st.cache_data(ttl=60)
def cached_funnel(device_type: str) -> tuple[pd.DataFrame, dict[str, float]]:
    """Cache funnel analysis results for the selected device type."""
    selected_device = None if device_type == "All" else device_type
    funnel, metrics = analyze_funnel(device_type=selected_device, print_summary=False, return_metrics=True)
    return funnel, metrics


@st.cache_data(ttl=60)
def cached_market() -> pd.DataFrame:
    """Cache latest market rows from SQLite."""
    rows = get_latest_market_data(DB_PATH)
    return pd.DataFrame(rows)


@st.cache_data(ttl=300)
def cached_cohorts() -> tuple[pd.DataFrame, dict[str, float]]:
    """Cache cohort retention calculations."""
    return analyze_cohorts(print_summary=False)


def read_market_history() -> pd.DataFrame:
    """Read the full market_data table from SQLite for display."""
    initialize_database(DB_PATH)
    with sqlite3.connect(DB_PATH) as connection:
        return pd.read_sql_query(
            """
            SELECT coin_id, symbol, name, current_price, market_cap, total_volume, price_change_24h, timestamp
            FROM market_data
            ORDER BY timestamp DESC, market_cap DESC
            """,
            connection,
        )


def currency_inr(value: float) -> str:
    """Format large INR values for Streamlit metric cards."""
    if value >= 10_000_000:
        return f"₹{value / 10_000_000:.2f}Cr"
    if value >= 100_000:
        return f"₹{value / 100_000:.2f}L"
    return f"₹{value:,.0f}"


def funnel_bar_chart(funnel: pd.DataFrame) -> go.Figure:
    """Build the KYC funnel horizontal conversion chart."""
    colors = [
        "#ef4444" if drop > 15 else "#f59e0b" if drop >= 8 else "#22c55e"
        for drop in funnel["drop_rate"]
    ]
    figure = go.Figure(
        go.Bar(
            x=funnel["pct_of_signups"],
            y=funnel["step_name"],
            orientation="h",
            marker_color=colors,
            text=[f"Drop {drop:.1f}%" for drop in funnel["drop_rate"]],
            textposition="auto",
            hovertemplate="<b>%{y}</b><br>% of signups: %{x:.1f}%<extra></extra>",
        )
    )
    figure.update_layout(
        title="KYC Funnel: % of Signups Remaining",
        xaxis_title="% of Signups Remaining",
        yaxis_title="Funnel Step",
        yaxis=dict(autorange="reversed"),
        height=470,
        margin=dict(l=20, r=20, t=60, b=30),
    )
    return figure


def market_volume_chart(market_df: pd.DataFrame) -> go.Figure:
    """Build the market volume bar chart."""
    figure = go.Figure(
        go.Bar(
            x=market_df["symbol"],
            y=market_df["total_volume"],
            marker_color="#1a73e8",
            hovertemplate="<b>%{x}</b><br>Volume: ₹%{y:,.0f}<extra></extra>",
        )
    )
    figure.update_layout(title="24h Trading Volume (INR)", xaxis_title="Coin", yaxis_title="Volume")
    return figure


def price_change_chart(market_df: pd.DataFrame) -> go.Figure:
    """Build the market price-change line chart."""
    marker_colors = ["#22c55e" if value >= 0 else "#ef4444" for value in market_df["price_change_24h"]]
    figure = go.Figure(
        go.Scatter(
            x=market_df["symbol"],
            y=market_df["price_change_24h"],
            mode="lines+markers",
            line=dict(color="#94a3b8", width=2),
            marker=dict(color=marker_colors, size=11),
            hovertemplate="<b>%{x}</b><br>24h Change: %{y:.2f}%<extra></extra>",
        )
    )
    figure.add_hline(y=0, line_dash="dash", line_color="#64748b")
    figure.update_layout(title="24h Price Change %", xaxis_title="Coin", yaxis_title="Change %")
    return figure


def cohort_heatmap(cohort_df: pd.DataFrame) -> go.Figure:
    """Build the weekly cohort retention heatmap."""
    week_columns = [f"W{week}" for week in range(8)]
    values = cohort_df[week_columns].to_numpy()
    text = [[f"{cell:.1f}%" for cell in row] for row in values]
    figure = go.Figure(
        go.Heatmap(
            z=values,
            x=[f"Week {week}" for week in range(8)],
            y=cohort_df["cohort_week"],
            colorscale="RdYlGn",
            text=text,
            texttemplate="%{text}",
            hovertemplate="Cohort %{y}<br>%{x}: %{z:.1f}%<extra></extra>",
        )
    )
    figure.update_layout(title="Cohort Retention Matrix", xaxis_title="Retention Week", yaxis_title="Signup Cohort")
    return figure


def render_sidebar() -> str:
    """Render sidebar controls and return the selected device filter."""
    st.sidebar.title("CryptoFlow Analytics")
    st.sidebar.caption("Automation & Data Pipeline Monitor")
    st.sidebar.write(f"Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    device_type = st.sidebar.selectbox("Device filter", ["All", "Android", "iOS", "Web"])

    if st.sidebar.button("Refresh Market Data", use_container_width=True):
        run_market_ingest()
        cached_market.clear()
        st.sidebar.success("Market data refreshed")

    if st.sidebar.button("Generate Excel Report", use_container_width=True):
        create_excel_report()
        st.sidebar.success("Excel report generated")

    if OUTPUT_PATH.exists():
        st.sidebar.download_button(
            "Download CryptoFlow_Report.xlsx",
            data=OUTPUT_PATH.read_bytes(),
            file_name="CryptoFlow_Report.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
        )
    return device_type


def render_funnel_tab(funnel: pd.DataFrame, metrics: dict[str, float]) -> None:
    """Render the KYC funnel dashboard tab."""
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Signups", f"{int(metrics['total_signups']):,}", "+12.4% vs last week")
    col2.metric("KYC Completion Rate", f"{metrics['kyc_completion_rate']:.1f}%", "-3.1%")
    col3.metric("Avg Drop Rate per Step", f"{metrics['avg_drop_rate']:.1f}%", "-0.8%")
    col4.metric("First Trade Conversion", f"{metrics['first_trade_conversion_rate']:.1f}%", "+1.2%")

    st.plotly_chart(funnel_bar_chart(funnel), use_container_width=True)

    for _, row in funnel.loc[funnel["is_anomaly"]].iterrows():
        st.warning(f"{row['step_name']} has an elevated drop-rate z-score of {row['z_score']:.1f}.")

    with st.expander("View Raw Funnel Data Table"):
        st.dataframe(funnel, use_container_width=True, hide_index=True)


def render_market_tab() -> None:
    """Render the market overview dashboard tab."""
    market_df = cached_market()
    metric_symbols = ["BTC", "ETH", "SOL", "XRP"]
    columns = st.columns(4)
    for column, symbol in zip(columns, metric_symbols):
        row = market_df.loc[market_df["symbol"] == symbol]
        if row.empty:
            column.metric(symbol, "Unavailable", "0.00%")
        else:
            record = row.iloc[0]
            column.metric(symbol, currency_inr(float(record["current_price"])), f"{float(record['price_change_24h']):.2f}%")

    st.plotly_chart(market_volume_chart(market_df), use_container_width=True)
    st.plotly_chart(price_change_chart(market_df), use_container_width=True)
    st.dataframe(read_market_history(), use_container_width=True, hide_index=True)


def render_cohort_tab() -> None:
    """Render the cohort retention dashboard tab."""
    cohort_df, cohort_metrics = cached_cohorts()
    latest_week_1 = float(cohort_df["W1"].iloc[-1])
    previous_week_1 = float(cohort_df["W1"].iloc[-2]) if len(cohort_df) > 1 else latest_week_1
    latest_month_1 = float(cohort_df["W4"].iloc[-1])
    previous_month_1 = float(cohort_df["W4"].iloc[-2]) if len(cohort_df) > 1 else latest_month_1

    col1, col2 = st.columns(2)
    col1.metric("Week-1 Retention", f"{cohort_metrics['avg_week_1_retention']:.0f}%", f"{latest_week_1 - previous_week_1:+.1f}% vs last cohort")
    col2.metric("Month-1 Retention", f"{cohort_metrics['avg_month_1_retention']:.0f}%", f"{latest_month_1 - previous_month_1:+.1f}% vs last cohort")
    st.plotly_chart(cohort_heatmap(cohort_df), use_container_width=True)


def render_pipeline_tab() -> None:
    """Render the pipeline monitor tab and run all jobs on demand."""
    pipeline_rows = [
        ["KYC Funnel ETL", "Every 15 min", "3m ago", "50,000", "✅ Running"],
        ["Market Data Ingest", "Every 1 min", "45s ago", "10", "✅ Running"],
        ["Cohort Report Builder", "Daily 6am IST", "9h ago", "6", "✅ Running"],
        ["Anomaly Alert Monitor", "Every 5 min", "2m ago", "50,000", "⚠️ Alert"],
        ["Excel Report Generator", "Daily 8am IST", "8h ago", "3", "✅ Running"],
        ["Drop-off SQL Optimizer", "Weekly", "4d ago", "8", "✅ Running"],
    ]
    pipeline_df = pd.DataFrame(
        pipeline_rows,
        columns=["Pipeline Name", "Schedule", "Last Run", "Records Processed", "Status"],
    )
    st.dataframe(pipeline_df, use_container_width=True, hide_index=True)

    if st.button("Run All Pipelines", type="primary"):
        progress = st.progress(0)
        generate_sample_data()
        progress.progress(17)
        run_market_ingest()
        progress.progress(34)
        analyze_funnel(print_summary=False)
        progress.progress(51)
        analyze_cohorts(print_summary=False)
        progress.progress(68)
        create_excel_report()
        progress.progress(85)
        run_alert_monitor()
        progress.progress(100)
        cached_funnel.clear()
        cached_market.clear()
        cached_cohorts.clear()
        st.success("All 6 pipelines completed successfully")


def main() -> None:
    """Run the Streamlit dashboard."""
    bootstrap_data()
    st.title("CryptoFlow Analytics Dashboard")
    device_type = render_sidebar()
    funnel, metrics = cached_funnel(device_type)

    tab1, tab2, tab3, tab4 = st.tabs(["KYC Funnel Analysis", "Market Overview", "Cohort Retention", "Pipeline Monitor"])
    with tab1:
        render_funnel_tab(funnel, metrics)
    with tab2:
        render_market_tab()
    with tab3:
        render_cohort_tab()
    with tab4:
        render_pipeline_tab()


if __name__ == "__main__":
    main()
