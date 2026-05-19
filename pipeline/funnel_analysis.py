"""KYC funnel analysis utilities for CryptoFlow."""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import zscore


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
DATA_PATH = PROJECT_ROOT / "data" / "funnel_events.csv"

FUNNEL_ORDER = [
    (1, "email_signup"),
    (2, "phone_otp"),
    (3, "pan_entry"),
    (4, "selfie_liveness"),
    (5, "bank_link"),
    (6, "kyc_approved"),
    (7, "first_deposit"),
    (8, "first_trade"),
]


def ensure_funnel_data(csv_path: Path = DATA_PATH) -> None:
    """Generate sample funnel data when the CSV is missing."""
    if csv_path.exists():
        return
    from data.generate_sample_data import main as generate_sample_data

    generate_sample_data()


def load_funnel_events(csv_path: Path = DATA_PATH) -> pd.DataFrame:
    """Load funnel events from CSV and normalize key columns."""
    ensure_funnel_data(csv_path)
    events = pd.read_csv(csv_path, parse_dates=["timestamp"])
    events["completed"] = events["completed"].astype(bool)
    return events


def analyze_funnel(
    device_type: str | None = None,
    csv_path: Path = DATA_PATH,
    print_summary: bool = True,
    return_metrics: bool = False,
) -> pd.DataFrame | tuple[pd.DataFrame, dict[str, float]]:
    """Compute reached users, cumulative conversion, drop rate, and anomalies by step."""
    events = load_funnel_events(csv_path)
    if device_type and device_type != "All":
        events = events.loc[events["device_type"] == device_type].copy()

    completed_events = events.loc[events["completed"]]
    rows: list[dict[str, object]] = []
    for step_order, step_name in FUNNEL_ORDER:
        step_users = completed_events.loc[completed_events["step_name"] == step_name, "user_id"].nunique()
        rows.append({"step_order": step_order, "step_name": step_name, "users_reached": int(step_users)})

    funnel = pd.DataFrame(rows)
    signup_count = float(funnel.loc[funnel["step_order"] == 1, "users_reached"].iloc[0] or 1)
    funnel["pct_of_signups"] = (funnel["users_reached"] / signup_count * 100).round(2)
    funnel["previous_users"] = funnel["users_reached"].shift(1)
    funnel["drop_rate"] = np.where(
        funnel["previous_users"].isna() | (funnel["previous_users"] == 0),
        0.0,
        (1 - (funnel["users_reached"] / funnel["previous_users"])) * 100,
    )
    funnel["drop_rate"] = funnel["drop_rate"].round(2)
    z_scores = zscore(funnel["drop_rate"].to_numpy(dtype=float), nan_policy="omit")
    funnel["z_score"] = np.nan_to_num(z_scores, nan=0.0).round(2)
    funnel["is_anomaly"] = funnel["z_score"] > 1.5
    funnel = funnel.drop(columns=["previous_users"])

    kyc_users = float(funnel.loc[funnel["step_name"] == "kyc_approved", "users_reached"].iloc[0])
    trade_users = float(funnel.loc[funnel["step_name"] == "first_trade", "users_reached"].iloc[0])
    metrics = {
        "total_signups": signup_count,
        "kyc_completion_rate": round(kyc_users / signup_count * 100, 2),
        "first_trade_conversion_rate": round(trade_users / signup_count * 100, 2),
        "avg_drop_rate": round(float(funnel.loc[funnel["step_order"] > 1, "drop_rate"].mean()), 2),
    }

    if print_summary:
        print("\nCryptoFlow KYC Funnel Summary")
        print(funnel.to_string(index=False))
        print(f"\nOverall KYC completion rate: {metrics['kyc_completion_rate']:.2f}%")
        print(f"First trade conversion rate: {metrics['first_trade_conversion_rate']:.2f}%")
        print("Funnel analysis completed successfully")

    if return_metrics:
        return funnel, metrics
    return funnel


def main() -> None:
    """CLI entry point for funnel analysis."""
    analyze_funnel(print_summary=True)


if __name__ == "__main__":
    main()
