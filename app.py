import math
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st


DATA_FILE = Path(__file__).with_name("ANALISA SLA.xlsx")

NUMERIC_COLUMNS = [
    "Total AWB",
    "OTP Existing",
    "Weighted Avg SLA Min Existing",
    "Weighted Avg SLA Max Existing",
    "P90 SLA Aktual",
    "P95 SLA Aktual",
    "Gap SLA P90",
    "Gap SLA P95",
]

FILTER_COLUMNS = [
    "Provinsi Asal",
    "Kota Asal",
    "Provinsi Tujuan",
    "Kota/Kab Tujuan",
    "Status Validasi SLA P95",
]

DISPLAY_COLUMNS = [
    "Provinsi Asal",
    "Kota Asal",
    "Provinsi Tujuan",
    "Kota/Kab Tujuan",
    "Total AWB",
    "OTP Existing",
    "Weighted Avg SLA Min Existing",
    "Weighted Avg SLA Max Existing",
    "P90 SLA Aktual",
    "P95 SLA Aktual",
    "Gap SLA P90",
    "Gap SLA P95",
    "Status Validasi SLA P90",
    "Status Validasi SLA P95",
]


def normalize_numeric(series: pd.Series) -> pd.Series:
    cleaned = (
        series.astype(str)
        .str.replace("%", "", regex=False)
        .str.replace(",", ".", regex=False)
        .str.strip()
    )
    return pd.to_numeric(cleaned, errors="coerce")


@st.cache_data(show_spinner=False)
def load_data() -> pd.DataFrame:
    if not DATA_FILE.exists():
        raise FileNotFoundError(f"File not found: {DATA_FILE}")
    df = pd.read_excel(DATA_FILE)

    df.columns = df.columns.str.strip()

    for column in NUMERIC_COLUMNS:
        if column in df.columns:
            df[column] = normalize_numeric(df[column])

    if "OTP Existing" in df.columns and df["OTP Existing"].dropna().max() <= 1:
        df["OTP Existing"] = df["OTP Existing"] * 100

    df["Rute"] = (
        df["Kota Asal"].astype(str).str.strip()
        + " -> "
        + df["Kota/Kab Tujuan"].astype(str).str.strip()
    )
    df["SLA Existing Mid"] = (
        df["Weighted Avg SLA Min Existing"] + df["Weighted Avg SLA Max Existing"]
    ) / 2
    df["SLA Existing Error Left"] = (
        df["SLA Existing Mid"] - df["Weighted Avg SLA Min Existing"]
    )
    df["SLA Existing Error Right"] = (
        df["Weighted Avg SLA Max Existing"] - df["SLA Existing Mid"]
    )

    return df


def build_comparison_chart(plot_df: pd.DataFrame) -> go.Figure:
    fig = go.Figure()

    for index, row in plot_df.iterrows():
        fig.add_trace(
            go.Scatter(
                x=[
                    row["Weighted Avg SLA Min Existing"],
                    row["Weighted Avg SLA Max Existing"],
                ],
                y=[row["Rute"], row["Rute"]],
                mode="lines",
                line=dict(color="rgba(78, 121, 167, 0.35)", width=18),
                name="Rentang SLA Existing",
                showlegend=index == 0,
                hovertemplate=(
                    "<b>%{y}</b><br>"
                    f"Min Existing: {row['Weighted Avg SLA Min Existing']:.2f} hari<br>"
                    f"Max Existing: {row['Weighted Avg SLA Max Existing']:.2f} hari"
                    "<extra></extra>"
                ),
            )
        )

    fig.add_trace(
        go.Scatter(
            x=plot_df["P90 SLA Aktual"],
            y=plot_df["Rute"],
            mode="markers",
            marker=dict(size=11, color="#2CA02C", symbol="circle"),
            name="P90 SLA Aktual",
            hovertemplate=(
                "<b>%{y}</b><br>"
                "P90 Aktual: %{x:.2f} hari"
                "<extra></extra>"
            ),
        )
    )

    fig.add_trace(
        go.Scatter(
            x=plot_df["P95 SLA Aktual"],
            y=plot_df["Rute"],
            mode="markers",
            marker=dict(size=13, color="#D62728", symbol="diamond"),
            name="P95 SLA Aktual",
            hovertemplate=(
                "<b>%{y}</b><br>"
                "P95 Aktual: %{x:.2f} hari"
                "<extra></extra>"
            ),
        )
    )

    max_value = plot_df[
        [
            "Weighted Avg SLA Min Existing",
            "Weighted Avg SLA Max Existing",
            "P90 SLA Aktual",
            "P95 SLA Aktual",
        ]
    ].max().max()
    max_value = 1 if pd.isna(max_value) else max_value

    fig.update_layout(
        height=max(520, len(plot_df) * 46),
        xaxis_title="Hari SLA",
        yaxis_title="Rute",
        hovermode="closest",
        margin=dict(l=260, r=40, t=80, b=40),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.03,
            xanchor="left",
            x=0,
            bgcolor="rgba(255,255,255,0.85)",
        ),
        showlegend=True,
        plot_bgcolor="white",
    )
    fig.update_xaxes(
        range=[0, math.ceil(max_value + 2)],
        gridcolor="#D9E2EC",
        zeroline=False,
    )
    fig.update_yaxes(autorange="reversed")
    return fig


def main() -> None:
    st.set_page_config(page_title="Dashboard Validasi SLA", layout="wide")
    st.title("Dashboard Validasi SLA Existing vs SLA Aktual")
    st.caption("Sumber data: ANALISA SLA.xlsx di folder proyek ini.")

    try:
        df = load_data()
    except Exception as exc:
        st.error(f"Gagal membaca data: {exc}")
        return

    st.sidebar.header("Filter")
    filtered = df.copy()

    for column in FILTER_COLUMNS:
        if column not in filtered.columns:
            continue
        options = sorted(filtered[column].dropna().astype(str).unique())
        selected = st.sidebar.multiselect(column, options)
        if selected:
            filtered = filtered[filtered[column].astype(str).isin(selected)]

    min_awb_default = 10 if "Total AWB" in filtered.columns else 0
    min_awb = st.sidebar.number_input(
        "Minimal Total AWB",
        min_value=0,
        value=min_awb_default,
        step=10,
    )
    if "Total AWB" in filtered.columns:
        filtered = filtered[filtered["Total AWB"].fillna(0) >= min_awb]

    sort_options = {
        "Gap SLA P95 terbesar": "Gap SLA P95",
        "P95 SLA Aktual terbesar": "P95 SLA Aktual",
        "Total AWB terbesar": "Total AWB",
    }
    sort_label = st.sidebar.selectbox(
        "Urutkan berdasarkan",
        list(sort_options.keys()),
    )
    sort_column = sort_options[sort_label]
    if sort_column in filtered.columns:
        filtered = filtered.sort_values(sort_column, ascending=False)

    max_routes = min(50, max(5, len(filtered))) if len(filtered) else 5
    top_n = st.sidebar.slider(
        "Jumlah rute ditampilkan",
        min_value=5,
        max_value=max_routes,
        value=min(15, max_routes),
        step=5,
    )

    if filtered.empty:
        st.warning("Tidak ada data yang cocok dengan filter saat ini.")
        return

    plot_df = filtered.head(top_n).copy()

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Rute", f"{len(filtered):,}")
    col2.metric("Total AWB", f"{filtered['Total AWB'].sum():,.0f}")

    total_awb = filtered["Total AWB"].sum()
    if total_awb > 0:
        weighted_otp = (filtered["OTP Existing"] * filtered["Total AWB"]).sum() / total_awb
        col3.metric("Weighted OTP Existing", f"{weighted_otp:.2f}%")
    else:
        col3.metric("Weighted OTP Existing", "-")

    need_revision = filtered["Status Validasi SLA P95"].astype(str).eq("Perlu Penambahan SLA").sum()
    col4.metric("Rute Perlu Penambahan SLA", f"{need_revision:,}")

    st.subheader("Visual Sederhana SLA Existing vs SLA Aktual")
    st.plotly_chart(build_comparison_chart(plot_df), use_container_width=True)

    st.subheader("Tabel Detail Rute")
    display_df = filtered[
        [column for column in DISPLAY_COLUMNS if column in filtered.columns]
    ].copy()
    if "OTP Existing" in display_df.columns:
        display_df["OTP Existing"] = display_df["OTP Existing"].map(
            lambda value: f"{value:.2f}%" if pd.notna(value) else ""
        )
    st.dataframe(display_df, use_container_width=True, hide_index=True)


if __name__ == "__main__":
    main()
