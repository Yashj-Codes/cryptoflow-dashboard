"""Anomaly alert monitor for CryptoFlow funnel health."""

from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from pipeline.funnel_analysis import analyze_funnel

ALERT_LOG_PATH = PROJECT_ROOT / "alerts" / "alert_log.txt"


def build_alert_messages() -> list[str]:
    """Evaluate funnel thresholds and return alert messages for current data."""
    funnel, metrics = analyze_funnel(print_summary=False, return_metrics=True)
    alerts: list[str] = []

    kyc_completion = metrics["kyc_completion_rate"]
    if kyc_completion < 35:
        alerts.append(f"ALERT: KYC completion at {kyc_completion:.1f}% — below 35% threshold")

    selfie_row = funnel.loc[funnel["step_name"] == "selfie_liveness"].iloc[0]
    selfie_drop = float(selfie_row["drop_rate"])
    if selfie_drop > 20:
        alerts.append(f"WARNING: Selfie drop at {selfie_drop:.1f}% — check app liveness SDK")

    anomalous_rows = funnel.loc[funnel["z_score"] > 2.0]
    for _, row in anomalous_rows.iterrows():
        alerts.append(f"ANOMALY: {row['step_name']} drop spike detected (z={float(row['z_score']):.1f})")

    return alerts


def append_alerts(alerts: list[str], log_path: Path = ALERT_LOG_PATH) -> None:
    """Append alert messages to a timestamped local log file."""
    if not alerts:
        return
    log_path.parent.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with log_path.open("a", encoding="utf-8") as handle:
        for message in alerts:
            handle.write(f"[{timestamp}] {message}\n")


def run_alert_monitor() -> list[str]:
    """Run all anomaly checks, printing only when a threshold is breached."""
    alerts = build_alert_messages()
    append_alerts(alerts)
    for message in alerts:
        print(message)
    return alerts


def main() -> None:
    """CLI entry point for anomaly alert monitoring."""
    run_alert_monitor()


if __name__ == "__main__":
    main()
