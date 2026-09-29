from __future__ import annotations

import json
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from statistics import mean

import pandas as pd
import streamlit as st


LOG_PATH = Path("data/logs.jsonl")
WINDOW_MINUTES = 60


def _parse_timestamp(value: str) -> datetime:
    timestamp = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if timestamp.tzinfo is None:
        timestamp = timestamp.replace(tzinfo=timezone.utc)
    return timestamp.astimezone(timezone.utc)


def _percentile(values: list[float], percentile: int) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = max(
        0,
        min(
            len(ordered) - 1,
            round((percentile / 100) * len(ordered) + 0.5) - 1,
        ),
    )
    return float(ordered[index])


def _load_records() -> list[dict]:
    if not LOG_PATH.exists():
        return []
    cutoff = datetime.now(timezone.utc) - timedelta(minutes=WINDOW_MINUTES)
    records: list[dict] = []
    for line in LOG_PATH.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            record = json.loads(line)
            record["_timestamp"] = _parse_timestamp(record["ts"])
        except (json.JSONDecodeError, KeyError, TypeError, ValueError):
            continue
        if record["_timestamp"] >= cutoff:
            records.append(record)
    return records


def _minute(record: dict) -> datetime:
    return record["_timestamp"].replace(second=0, microsecond=0)


def _frame(rows: list[dict]) -> pd.DataFrame:
    if not rows:
        return pd.DataFrame()
    return pd.DataFrame(rows).sort_values("minute").set_index("minute")


st.set_page_config(page_title="Day 13 Monitoring & LLMOps", layout="wide")
st.markdown('<meta http-equiv="refresh" content="30">', unsafe_allow_html=True)
st.title("K4-L3A Day 13 Monitoring & LLMOps")
st.caption("Source: data/logs.jsonl | Time range: last 60 minutes | Refresh: 30 seconds")

records = _load_records()
if not records:
    st.warning("No log data in the last 60 minutes. Run scripts/load_test.py first.")
    st.stop()

received = [item for item in records if item.get("event") == "request_received"]
responses = [item for item in records if item.get("event") == "response_sent"]
failures = [item for item in records if item.get("event") == "request_failed"]

response_groups: dict[datetime, list[dict]] = defaultdict(list)
request_groups: dict[datetime, list[dict]] = defaultdict(list)
failure_groups: dict[datetime, list[dict]] = defaultdict(list)
tool_groups: dict[datetime, list[dict]] = defaultdict(list)

for item in responses:
    response_groups[_minute(item)].append(item)
for item in received:
    request_groups[_minute(item)].append(item)
for item in failures:
    failure_groups[_minute(item)].append(item)
for item in records:
    if item.get("tool_success") is not None:
        tool_groups[_minute(item)].append(item)

latencies = [float(item.get("latency_ms", 0)) for item in responses]
ttfts = [float(item.get("ttft_ms", 0)) for item in responses]
quality_scores = [float(item.get("quality_score", 0)) for item in responses]

latency_rows = []
for minute, items in response_groups.items():
    values = [float(item.get("latency_ms", 0)) for item in items]
    ttft_values = [float(item.get("ttft_ms", 0)) for item in items]
    latency_rows.append(
        {
            "minute": minute,
            "latency_p50": _percentile(values, 50),
            "latency_p95": _percentile(values, 95),
            "latency_p99": _percentile(values, 99),
            "ttft_p95": _percentile(ttft_values, 95),
            "slo_3000_ms": 3000,
        }
    )

traffic_rows = [
    {"minute": minute, "requests_per_minute": len(items), "threshold": 1}
    for minute, items in request_groups.items()
]

error_rows = []
all_minutes = sorted(set(request_groups) | set(failure_groups) | set(tool_groups))
for minute in all_minutes:
    request_count = len(request_groups.get(minute, []))
    failure_count = len(failure_groups.get(minute, []))
    tool_events = tool_groups.get(minute, [])
    error_rows.append(
        {
            "minute": minute,
            "error_rate_pct": failure_count / request_count * 100 if request_count else 0.0,
            "error_rate_limit": 2.0,
            "retrieval_success_pct": (
                sum(item.get("tool_success") is True for item in tool_events)
                / len(tool_events)
                * 100
                if tool_events
                else 100.0
            ),
            "retrieval_minimum": 90.0,
        }
    )

cost_rows = []
cumulative_cost = 0.0
for minute in sorted(response_groups):
    minute_cost = sum(float(item.get("cost_usd", 0)) for item in response_groups[minute])
    cumulative_cost += minute_cost
    cost_rows.append(
        {
            "minute": minute,
            "cost_usd_per_minute": minute_cost,
            "cumulative_cost_usd": cumulative_cost,
            "budget_usd": 2.5,
        }
    )

token_rows = [
    {
        "minute": minute,
        "tokens_in": sum(int(item.get("tokens_in", 0)) for item in items),
        "tokens_out": sum(int(item.get("tokens_out", 0)) for item in items),
    }
    for minute, items in response_groups.items()
]

quality_rows = [
    {
        "minute": minute,
        "quality_average": mean(float(item.get("quality_score", 0)) for item in items),
        "quality_minimum": 0.75,
    }
    for minute, items in response_groups.items()
]

left, right = st.columns(2)
with left:
    st.subheader("1. Latency percentiles and TTFT")
    p50, p95, p99, ttft = st.columns(4)
    p50.metric("P50", f"{_percentile(latencies, 50):.0f} ms")
    p95.metric("P95", f"{_percentile(latencies, 95):.0f} ms")
    p99.metric("P99", f"{_percentile(latencies, 99):.0f} ms")
    ttft.metric("TTFT P95", f"{_percentile(ttfts, 95):.0f} ms")
    st.line_chart(_frame(latency_rows))
    st.caption("SLO: latency P95 <= 3000 ms")

with right:
    st.subheader("2. Request traffic")
    st.metric("Requests in window", len(received))
    st.line_chart(_frame(traffic_rows))
    st.caption("Threshold: traffic >= 1 request/minute")

left, right = st.columns(2)
with left:
    st.subheader("3. Errors and retrieval success")
    error_rate = len(failures) / len(received) * 100 if received else 0.0
    tool_events = [item for item in records if item.get("tool_success") is not None]
    retrieval_success = (
        sum(item.get("tool_success") is True for item in tool_events)
        / len(tool_events)
        * 100
        if tool_events
        else 100.0
    )
    error_col, retrieval_col = st.columns(2)
    error_col.metric("Error rate", f"{error_rate:.2f}%")
    retrieval_col.metric("Retrieval success", f"{retrieval_success:.2f}%")
    st.line_chart(_frame(error_rows))
    st.write("Error breakdown:", dict(Counter(item.get("error_type", "unknown") for item in failures)))
    st.caption("Thresholds: error rate <= 2%; retrieval success >= 90%")

with right:
    st.subheader("4. Cost over time")
    st.metric("Total cost", f"${sum(float(item.get('cost_usd', 0)) for item in responses):.6f}")
    st.line_chart(_frame(cost_rows))
    st.caption("Budget: total cost <= $2.50")

left, right = st.columns(2)
with left:
    st.subheader("5. Input and output tokens")
    token_in_col, token_out_col = st.columns(2)
    token_in_col.metric("Input tokens", sum(int(item.get("tokens_in", 0)) for item in responses))
    token_out_col.metric("Output tokens", sum(int(item.get("tokens_out", 0)) for item in responses))
    st.line_chart(_frame(token_rows))
    st.caption("Guardrail: total tokens <= 50,000")

with right:
    st.subheader("6. Quality proxy")
    st.metric("Average quality", f"{mean(quality_scores) if quality_scores else 0.0:.3f}")
    st.line_chart(_frame(quality_rows))
    st.caption("Threshold: mean quality >= 0.75")
