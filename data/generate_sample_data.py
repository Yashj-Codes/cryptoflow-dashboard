"""Generate synthetic CryptoFlow KYC funnel event data."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_PATH = PROJECT_ROOT / "data" / "funnel_events.csv"
TOTAL_SIGNUPS = 50_000
RANDOM_SEED = 42

FUNNEL_STEPS = [
    ("email_signup", 1, 1.000),
    ("phone_otp", 2, 0.840),
    ("pan_entry", 3, 0.670),
    ("selfie_liveness", 4, 0.510),
    ("bank_link", 5, 0.420),
    ("kyc_approved", 6, 0.382),
    ("first_deposit", 7, 0.222),
    ("first_trade", 8, 0.140),
]

DEVICE_TYPES = ["Android", "iOS", "Web"]
DEVICE_PROBABILITIES = [0.60, 0.25, 0.15]
CITIES = ["Mumbai", "Delhi", "Bangalore", "Hyderabad", "Pune", "Indore", "Nagpur", "Lucknow"]


def build_funnel_events(total_signups: int = TOTAL_SIGNUPS) -> pd.DataFrame:
    """Create deterministic synthetic user events across the KYC funnel."""
    rng = np.random.default_rng(RANDOM_SEED)
    user_ids = np.arange(1, total_signups + 1)
    shuffled_users = rng.permutation(user_ids)

    devices = rng.choice(DEVICE_TYPES, size=total_signups, p=DEVICE_PROBABILITIES)
    cities = rng.choice(CITIES, size=total_signups)
    session_numbers = rng.integers(100_000, 999_999, size=total_signups)

    user_profile = pd.DataFrame(
        {
            "user_id": user_ids,
            "device_type": devices,
            "city": cities,
            "session_id": [f"sess_{number}" for number in session_numbers],
            "signup_timestamp": pd.Timestamp.utcnow().tz_localize(None)
            - pd.to_timedelta(rng.integers(0, 90 * 24 * 60, size=total_signups), unit="m"),
        }
    ).set_index("user_id")

    rows: list[dict[str, object]] = []
    for step_name, step_order, reach_rate in FUNNEL_STEPS:
        users_reached = int(round(total_signups * reach_rate))
        reached_user_ids = shuffled_users[:users_reached]
        step_offsets = rng.integers(0, 72 * 60, size=users_reached) + (step_order - 1) * 30

        for user_id, offset_minutes in zip(reached_user_ids, step_offsets):
            profile = user_profile.loc[user_id]
            rows.append(
                {
                    "user_id": f"user_{int(user_id):05d}",
                    "session_id": profile["session_id"],
                    "step_name": step_name,
                    "step_order": step_order,
                    "device_type": profile["device_type"],
                    "city": profile["city"],
                    "timestamp": (profile["signup_timestamp"] + pd.Timedelta(minutes=int(offset_minutes))).isoformat(),
                    "completed": True,
                }
            )

    events = pd.DataFrame(rows)
    events = events.sort_values(["user_id", "step_order", "timestamp"]).reset_index(drop=True)
    return events


def main() -> None:
    """Generate the CSV file used by the dashboard and downstream pipelines."""
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    events = build_funnel_events()
    events.to_csv(OUTPUT_PATH, index=False)
    print("Generated 50,000 funnel events successfully")


if __name__ == "__main__":
    main()
