from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd
import streamlit as st
import altair as alt

# This UI is separate from the generator. It only reads files produced by main.py.
PROJECT_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = PROJECT_DIR / "output"

st.set_page_config(
    page_title="YottaFlex OEE | Manufacturing Insights",
    page_icon="🏭",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
      .stApp { background: #f5f7fb; color: #172033; }
      [data-testid="stSidebar"] { background: #ffffff; border-right: 1px solid #e3e8f0; }
      .block-container { padding-top: 1.6rem; padding-bottom: 2rem; }
      .hero {
        background: linear-gradient(115deg, #ffffff 0%, #edf4ff 100%);
        border: 1px solid #dce7f7; border-radius: 18px;
        padding: 1.25rem 1.5rem; margin-bottom: 1rem;
      }
      .hero h1 { color: #173b70; margin: 0; font-size: 2rem; }
      .hero p { color: #52647d; margin: .45rem 0 0 0; }
      div[data-testid="stMetric"] {
        background: #ffffff; border: 1px solid #e1e7f0;
        border-radius: 14px; padding: 14px 16px;
      }
      div[data-testid="stMetricLabel"] { color: #5d6b82; }
      div[data-testid="stMetricValue"] { color: #163f78; }
      .section-note { color: #64748b; font-size: .9rem; }
    </style>
    """,
    unsafe_allow_html=True,
)


def find_file(base_name: str) -> Path | None:
    """Find a generated CSV/JSON file in output/ without changing project files."""
    direct = OUTPUT_DIR / base_name
    if direct.exists():
        return direct
    matches = list(OUTPUT_DIR.rglob(base_name)) if OUTPUT_DIR.exists() else []
    return matches[0] if matches else None


@st.cache_data(show_spinner=False)
def read_csv_file(path_string: str) -> pd.DataFrame:
    return pd.read_csv(path_string, low_memory=False)


@st.cache_data(show_spinner=False)
def read_json_file(path_string: str) -> Any:
    with open(path_string, "r", encoding="utf-8") as file:
        return json.load(file)


def load_csvs() -> dict[str, tuple[Path, pd.DataFrame]]:
    found: dict[str, tuple[Path, pd.DataFrame]] = {}
    if not OUTPUT_DIR.exists():
        return found
    for path in sorted(OUTPUT_DIR.rglob("*.csv")):
        # Do not load temporary or nested duplicate test outputs.
        if any(part.startswith(".") for part in path.parts):
            continue
        try:
            frame = read_csv_file(str(path))
            found[path.stem] = (path, frame)
        except Exception:
            continue
    return found


def first_matching_column(columns: list[str], candidates: list[str]) -> str | None:
    lookup = {column.lower().strip(): column for column in columns}
    for candidate in candidates:
        if candidate.lower() in lookup:
            return lookup[candidate.lower()]
    for column in columns:
        low = column.lower().strip()
        if any(candidate.lower() in low for candidate in candidates):
            return column
    return None


def number_series(frame: pd.DataFrame, column: str | None) -> pd.Series:
    if not column or column not in frame.columns:
        return pd.Series(dtype="float64")
    return pd.to_numeric(frame[column], errors="coerce").dropna()


def fmt_percent(value: float) -> str:
    # Values in exported OEE files are often stored either as 0-1 fractions or 0-100 percentages.
    if value <= 1.0:
        value *= 100
    return f"{value:.1f}%"


st.markdown(
    """
    <div class="hero">
      <h1>YottaFlex OEE Dashboard</h1>
      <p>Manufacturing performance, machine events, quality checks, and validation results.</p>
    </div>
    """,
    unsafe_allow_html=True,
)

with st.sidebar:
    st.header("Dashboard controls")
    st.caption("This dashboard reads existing exports. It does not modify or regenerate them.")
    output_text = st.text_input("Output folder", value=str(OUTPUT_DIR))
    custom_output_dir = Path(output_text).expanduser()
    if not custom_output_dir.is_absolute():
        custom_output_dir = (PROJECT_DIR / custom_output_dir).resolve()
    st.divider()
    st.caption("To create or refresh the exports, run your existing main.py command in PowerShell.")

# Allow the user to point the dashboard at any generated output folder.
OUTPUT_DIR = custom_output_dir
csv_files = load_csvs()

if not OUTPUT_DIR.exists():
    st.error(f"Output folder not found: {OUTPUT_DIR}")
    st.info("Run your generator first, for example: `python main.py --output output --seed 42`")
    st.stop()

if not csv_files:
    st.warning(f"No CSV files were found in `{OUTPUT_DIR}`.")
    st.info("Run the generator and make sure it writes CSV exports into the selected output folder.")
    st.stop()

# Identify likely core tables; use the first available CSV when names differ.
def get_table(*names: str) -> pd.DataFrame:
    for name in names:
        if name in csv_files:
            return csv_files[name][1]
    return pd.DataFrame()


oee_df = get_table("oee_metrics", "shift_oee_metrics")
events_df = get_table("machine_events")
counts_df = get_table("production_counts")
quality_df = get_table("quality_inspections")
machines_df = get_table("machines")
lines_df = get_table("lines")
anomalies_df = get_table("anomaly_labels")
orders_df = get_table("production_orders")

# If no exact OEE table was found, look for a CSV whose name contains "oee".
if oee_df.empty:
    for table_name, (_, frame) in csv_files.items():
        if "oee" in table_name.lower():
            oee_df = frame
            break

# Sidebar filters apply only when compatible columns exist.
st.sidebar.subheader("Filters")
filtered_oee = oee_df.copy()
machine_col = first_matching_column(list(filtered_oee.columns), ["machine_id", "machine"])
line_col = first_matching_column(list(filtered_oee.columns), ["line_id", "line"])
shift_col = first_matching_column(list(filtered_oee.columns), ["shift_id", "shift"])
if machine_col:
    options = sorted(filtered_oee[machine_col].dropna().astype(str).unique().tolist())
    chosen = st.sidebar.multiselect("Machine", options, default=[])
    if chosen:
        filtered_oee = filtered_oee[filtered_oee[machine_col].astype(str).isin(chosen)]
if line_col:
    options = sorted(filtered_oee[line_col].dropna().astype(str).unique().tolist())
    chosen = st.sidebar.multiselect("Production line", options, default=[])
    if chosen:
        filtered_oee = filtered_oee[filtered_oee[line_col].astype(str).isin(chosen)]
if shift_col:
    options = sorted(filtered_oee[shift_col].dropna().astype(str).unique().tolist())
    chosen = st.sidebar.multiselect("Shift", options, default=[])
    if chosen:
        filtered_oee = filtered_oee[filtered_oee[shift_col].astype(str).isin(chosen)]

# KPI values are inferred from the column names in the generated schema.
oee_col = first_matching_column(list(filtered_oee.columns), ["oee", "overall_equipment_effectiveness"])
availability_col = first_matching_column(list(filtered_oee.columns), ["availability"])
performance_col = first_matching_column(list(filtered_oee.columns), ["performance"])
quality_oee_col = first_matching_column(list(filtered_oee.columns), ["quality_rate", "quality"])
def mean_value(frame: pd.DataFrame, column: str | None) -> float | None:
    values = number_series(frame, column)
    return float(values.mean()) if not values.empty else None

def display_pct(value: float | None) -> str:
    if value is None:
        return "N/A"
    return fmt_percent(value)

total_machines = len(machines_df) if not machines_df.empty else (
    events_df[first_matching_column(list(events_df.columns), ["machine_id"])].nunique()
    if not events_df.empty and first_matching_column(list(events_df.columns), ["machine_id"]) else 0
)
total_events = len(events_df)
total_quality = len(quality_df)
total_anomalies = len(anomalies_df)

metric1, metric2, metric3, metric4 = st.columns(4)
with metric1:
    st.metric("Average OEE", display_pct(mean_value(filtered_oee, oee_col)))
with metric2:
    st.metric("Availability", display_pct(mean_value(filtered_oee, availability_col)))
with metric3:
    st.metric("Performance", display_pct(mean_value(filtered_oee, performance_col)))
with metric4:
    st.metric("Machines", f"{total_machines:,}")

metric5, metric6, metric7, metric8 = st.columns(4)
with metric5:
    st.metric("Machine events", f"{total_events:,}")
with metric6:
    st.metric("Production count rows", f"{len(counts_df):,}")
with metric7:
    st.metric("Quality inspections", f"{total_quality:,}")
with metric8:
    st.metric("Anomaly label rows", f"{total_anomalies:,}")

tab_overview, tab_machines, tab_data, tab_validation = st.tabs(
    ["Overview", "Machine & quality", "Data explorer", "Validation & exports"]
)

with tab_overview:
    st.subheader("OEE performance")

    if filtered_oee.empty:
        st.info("No OEE rows are available in the selected table or filters.")
    else:
        numeric_columns = filtered_oee.select_dtypes(
            include="number"
        ).columns.tolist()
        column_lookup = {col.lower().strip(): col for col in numeric_columns}

        # Select only the intended rate columns; do not chart every numeric field.
        candidates = [
            (["oee_percent", "oee"], "OEE"),
            (["availability"], "Availability"),
            (["performance"], "Performance"),
            (["quality_rate", "quality"], "Quality"),
        ]
        selected = []
        used_columns = set()
        for names, label in candidates:
            matched = next(
                (
                    column_lookup[name]
                    for name in names
                    if name in column_lookup and column_lookup[name] not in used_columns
                ),
                None,
            )
            if matched:
                selected.append((matched, label))
                used_columns.add(matched)

        if not selected:
            st.info(
                "No numeric OEE/availability/performance/quality columns were detected."
            )
        else:
            st.caption(
                "Each metric is charted separately on a 0–100% scale to avoid "
                "mixing unrelated scales. Invalid values are reported, not silently changed."
            )
            chart_source = filtered_oee.head(2000).copy()
            if len(filtered_oee) > 2000:
                st.caption("Charts use the first 2,000 filtered records for readability.")

            chart_columns = st.columns(2)
            for index, (source_column, label) in enumerate(selected):
                values = pd.to_numeric(
                    chart_source[source_column], errors="coerce"
                )
                observed = values.dropna()

                # Convert fractional rates to percentages when all observed values
                # fit the conventional 0–1 fraction range.
                if not observed.empty and observed.min() >= 0 and observed.max() <= 1:
                    values = values * 100

                invalid_mask = values.notna() & ((values < 0) | (values > 100))
                invalid_count = int(invalid_mask.sum())
                plot_values = values.mask(invalid_mask)

                with chart_columns[index % 2]:
                    st.markdown(f"**{label} (%)**")
                    plot_frame = pd.DataFrame(
                        {
                            "Record": range(1, len(plot_values) + 1),
                            "Percentage": plot_values.reset_index(drop=True),
                        }
                    )
                    chart = (
                        alt.Chart(plot_frame)
                        .mark_line()
                        .encode(
                            x=alt.X("Record:Q", title="Record"),
                            y=alt.Y(
                                "Percentage:Q",
                                title=f"{label} (%)",
                                scale=alt.Scale(domain=[0, 100], clamp=True),
                            ),
                            tooltip=[
                                alt.Tooltip("Record:Q", title="Record"),
                                alt.Tooltip(
                                    "Percentage:Q",
                                    title=f"{label} (%)",
                                    format=".2f",
                                ),
                            ],
                        )
                        .properties(height=260)
                    )
                    st.altair_chart(chart, use_container_width=True)
                    if invalid_count:
                        st.warning(
                            f"{label}: {invalid_count} of the displayed records are "
                            "outside 0–100% and are omitted from this chart. "
                            "The underlying data remains unchanged."
                        )

        st.subheader("OEE records")
        st.dataframe(
            filtered_oee.head(1000),
            width="stretch",
            hide_index=True,
        )
        st.caption("Showing up to 1,000 rows in the preview.")

with tab_machines:
    left, right = st.columns(2)
    with left:
        st.subheader("Machine events")
        if events_df.empty:
            st.info("No machine_events.csv table was found.")
        else:
            reason_col = first_matching_column(list(events_df.columns), ["reason", "event_type", "event_code"])
            if reason_col:
                reason_counts = events_df[reason_col].fillna("Unknown").astype(str).value_counts().head(15)
                st.bar_chart(reason_counts)
                st.caption(f"Grouped by `{reason_col}`.")
            st.dataframe(events_df.head(500), width="stretch", hide_index=True)
    with right:
        st.subheader("Quality inspections")
        if quality_df.empty:
            st.info("No quality_inspections.csv table was found.")
        else:
            result_col = first_matching_column(list(quality_df.columns), ["result", "status", "outcome", "passed"])
            if result_col:
                result_counts = quality_df[result_col].fillna("Unknown").astype(str).value_counts()
                st.bar_chart(result_counts)
            st.dataframe(quality_df.head(500), width="stretch", hide_index=True)
    st.subheader("Anomaly labels")
    if anomalies_df.empty:
        st.info("No anomaly_labels.csv table was found.")
    else:
        st.dataframe(anomalies_df, width="stretch", hide_index=True)

with tab_data:
    st.subheader("Explore generated tables")
    table_name = st.selectbox("Choose a CSV table", options=sorted(csv_files.keys()))
    table_path, table_frame = csv_files[table_name]
    st.caption(f"File: `{table_path.relative_to(OUTPUT_DIR) if table_path.is_relative_to(OUTPUT_DIR) else table_path}`")
    st.write(f"Rows: **{len(table_frame):,}** | Columns: **{len(table_frame.columns)}**")
    search_text = st.text_input("Search visible text in this table", placeholder="Type an ID, status, reason, or value")
    preview = table_frame
    if search_text.strip():
        mask = preview.astype(str).apply(
            lambda column: column.str.contains(search_text.strip(), case=False, na=False, regex=False)
        ).any(axis=1)
        preview = preview[mask]
    st.dataframe(preview.head(2000), width="stretch", hide_index=True)
    st.caption("The on-screen preview is capped at 2,000 rows to keep the dashboard responsive.")
    st.download_button(
        "Download selected table as CSV",
        data=table_frame.to_csv(index=False).encode("utf-8"),
        file_name=f"{table_name}.csv",
        mime="text/csv",
    )

with tab_validation:
    st.subheader("Validation report")
    validation_path = find_file("validation_report.json")
    manifest_path = find_file("manifest.json")
    schema_path = find_file("schema.sql")
    if validation_path:
        try:
            validation_report = read_json_file(str(validation_path))
            st.json(validation_report)
            st.download_button(
                "Download validation report",
                data=json.dumps(validation_report, indent=2).encode("utf-8"),
                file_name="validation_report.json",
                mime="application/json",
            )
        except Exception as exc:
            st.warning(f"Could not read validation_report.json: {exc}")
    else:
        st.info("validation_report.json was not found in this output folder.")
    st.subheader("Manifest and SQL schema")
    if manifest_path:
        try:
            manifest = read_json_file(str(manifest_path))
            st.download_button(
                "Download manifest.json",
                data=json.dumps(manifest, indent=2).encode("utf-8"),
                file_name="manifest.json",
                mime="application/json",
            )
            with st.expander("View manifest"):
                st.json(manifest)
        except Exception as exc:
            st.warning(f"Could not read manifest.json: {exc}")
    else:
        st.info("manifest.json was not found in this output folder.")
    if schema_path:
        schema_text = schema_path.read_text(encoding="utf-8")
        st.download_button(
            "Download schema.sql",
            data=schema_text.encode("utf-8"),
            file_name="schema.sql",
            mime="text/plain",
        )
        with st.expander("View SQL schema"):
            st.code(schema_text, language="sql")
    else:
        st.info("schema.sql was not found in this output folder.")

st.divider()
st.markdown(
    '<p class="section-note">YottaFlex OEE Challenge | Read-only dashboard | Generated exports remain unchanged.</p>',
    unsafe_allow_html=True,
)
