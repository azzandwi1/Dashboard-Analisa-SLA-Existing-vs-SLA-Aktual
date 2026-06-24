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


def render_methodology_note() -> None:
    with st.expander("Catatan: P90, P95, dan Weighted Average"):
        st.markdown(
            """
            **Disclaimer**

            Dashboard ini membaca rute pada level `Kota Asal -> Kota Tujuan`.
            Sementara SLA existing bisa tersimpan lebih detail pada level
            `Kota Asal -> Kecamatan Tujuan`.
            Karena itu, ketika SLA existing diringkas ke level kota tujuan,
            pendekatan yang dipakai adalah `weighted average` agar hasilnya
            tetap mewakili komposisi AWB per kecamatan.

            **Apa itu P90 dan P95**

            - `P90 SLA Aktual` adalah nilai SLA di mana `90%` pengiriman selesai pada atau sebelum angka itu.
            - `P95 SLA Aktual` adalah nilai SLA di mana `95%` pengiriman selesai pada atau sebelum angka itu.

            Contoh sederhana:
            Jika `P90 = 3 hari`, artinya `90 dari 100` pengiriman selesai maksimal `3 hari`.
            Jika `P95 = 5 hari`, artinya `95 dari 100` pengiriman selesai maksimal `5 hari`.

            **Kenapa memakai weighted average**

            Dalam analisa ini, weighted average lebih representatif daripada average biasa,
            karena setiap kecamatan tujuan memiliki volume `AWB` yang berbeda.
            Kecamatan dengan volume kiriman besar seharusnya punya pengaruh lebih besar
            dibanding kecamatan dengan volume kecil.

            Kalau memakai average biasa, semua kecamatan dianggap sama besar,
            padahal kondisi operasional nyatanya tidak seperti itu.

            **Rumus weighted average**

            `Weighted Average = Σ(nilai × bobot) / Σ(bobot)`

            Di dashboard ini, bobot yang dipakai adalah `Total AWB`.

            **Contoh sederhana**

            Misal ada 2 kecamatan tujuan dalam 1 kota:

            - Kecamatan A: `AWB = 10.000`, `Max SLA = 2 hari`
            - Kecamatan B: `AWB = 100`, `Max SLA = 10 hari`

            Jika pakai **average biasa**:

            `(2 + 10) / 2 = 6 hari`

            Hasil `6 hari` ini menyesatkan, karena hampir semua kiriman sebenarnya menuju Kecamatan A
            yang SLA-nya hanya `2 hari`.

            Jika pakai **weighted average**:

            `((10.000 × 2) + (100 × 10)) / (10.000 + 100)`

            `= 21.000 / 10.100 = 2,08 hari`

            Hasil `2,08 hari` jauh lebih mencerminkan kondisi operasional sebenarnya.

            **Kenapa penting untuk analisa SLA ini**

            Di dashboard ini, Anda membandingkan:

            - `SLA Existing`
            - `P90 SLA Aktual`
            - `P95 SLA Aktual`

            pada level:

            - `Kota Asal -> Kota Tujuan`

            Sementara data SLA existing bisa berasal dari level yang lebih detail,
            misalnya `Kota Asal -> Kecamatan Tujuan`.
            Dalam satu kota tujuan bisa ada banyak kecamatan dengan SLA berbeda.

            Contoh:

            - Cengkareng: `AWB = 5.000`, `Max SLA = 2`
            - Kalideres: `AWB = 4.000`, `Max SLA = 2`
            - Kapuk: `AWB = 3.000`, `Max SLA = 2`
            - Kepulauan Seribu: `AWB = 50`, `Max SLA = 7`

            Jika pakai **average biasa**:

            `(2 + 2 + 2 + 7) / 4 = 3,25 hari`

            Padahal mayoritas kiriman ada di SLA `2 hari`.

            Jika pakai **weighted average**:

            `((5.000×2) + (4.000×2) + (3.000×2) + (50×7)) / 12.050`

            `= 24.350 / 12.050 = 2,02 hari`

            Hasil ini lebih realistis untuk dijadikan benchmark.

            **Kenapa tidak langsung pakai SLA Max terbesar**

            Kalau langsung pakai SLA max terbesar, benchmark bisa jadi terlalu longgar.

            Misal dalam satu kota tujuan ada SLA:

            - `2`
            - `2`
            - `2`
            - `2`
            - `7`

            Kalau benchmark yang dipakai hanya `7`, maka `P95 Aktual = 5` akan terlihat masih aman.
            Padahal mayoritas area sebenarnya berjalan dengan SLA existing `2 hari`.

            """
        )


def main() -> None:
    st.set_page_config(page_title="Dashboard Analisa SLA", layout="wide")
    st.title("Dashboard Analisa SLA Existing vs SLA Aktual")
    render_methodology_note()

    try:
        df = load_data()
    except Exception as exc:
        st.error(f"Gagal membaca data: {exc}")
        return

    st.sidebar.header("Filter")
    selected_filters: dict[str, list[str]] = {}

    for column in FILTER_COLUMNS:
        if column not in df.columns:
            continue
        options = sorted(df[column].dropna().astype(str).unique())
        selected_filters[column] = st.sidebar.multiselect(
            column,
            options,
            key=f"filter_{column}",
        )

    filtered = df.copy()
    for column, selected in selected_filters.items():
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
        index=2,
    )
    sort_column = sort_options[sort_label]
    if sort_column in filtered.columns:
        filtered = filtered.sort_values(sort_column, ascending=False)

    if filtered.empty:
        st.warning("Tidak ada data yang cocok dengan filter saat ini.")
        return

    route_count = len(filtered)
    if route_count <= 5:
        top_n = route_count
        st.sidebar.caption(f"Jumlah rute ditampilkan: {top_n}")
    else:
        max_routes = min(50, route_count)
        default_top_n = min(15, max_routes)
        top_n = st.sidebar.slider(
            "Jumlah rute ditampilkan",
            min_value=5,
            max_value=max_routes,
            value=default_top_n,
            step=5,
        )

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
