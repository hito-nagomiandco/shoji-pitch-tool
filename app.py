import uuid
from pathlib import Path

import pandas as pd
import streamlit as st

from shoji_panel_calculator import (
    ShojiPanelParams,
    calculate_shoji_panel,
    plot_shoji_panel,
)


st.set_page_config(
    page_title="障子ピッチツール",
    page_icon="▥",
    layout="centered",
    initial_sidebar_state="collapsed",
)

st.markdown(
    """
    <style>
    .block-container {
        padding-top: 1rem;
        padding-left: 1rem;
        padding-right: 1rem;
        max-width: 760px;
    }
    div.stButton > button,
    div.stDownloadButton > button {
        width: 100%;
        min-height: 3.0rem;
        border-radius: 0.75rem;
        font-size: 1.05rem;
    }
    [data-testid="stMetricValue"] {
        font-size: 1.25rem;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

st.title("障子ピッチツール")
st.caption("1枚の小パネル用｜曲線的に変化する縦組子の間隔を計算・可視化")


# --------------------------
# Presets
# --------------------------
preset = st.selectbox(
    "プリセット",
    [
        "360×600 / 18本 / 右に密",
        "360×600 / 18本 / 左に密",
        "360×600 / 18本 / 中央に密",
        "カスタム",
    ],
)

if preset == "360×600 / 18本 / 右に密":
    default = dict(panel_width=360.0, panel_height=600.0, bar_width=5.0, bar_thickness=12.0,
                   bar_count=18, variation_percent=70.0, curve_type="cosine", curve_strength=2.0,
                   direction="right_dense")
elif preset == "360×600 / 18本 / 左に密":
    default = dict(panel_width=360.0, panel_height=600.0, bar_width=5.0, bar_thickness=12.0,
                   bar_count=18, variation_percent=70.0, curve_type="cosine", curve_strength=2.0,
                   direction="left_dense")
elif preset == "360×600 / 18本 / 中央に密":
    default = dict(panel_width=360.0, panel_height=600.0, bar_width=5.0, bar_thickness=12.0,
                   bar_count=18, variation_percent=70.0, curve_type="cosine", curve_strength=2.0,
                   direction="center_dense")
else:
    default = dict(panel_width=360.0, panel_height=600.0, bar_width=5.0, bar_thickness=12.0,
                   bar_count=18, variation_percent=70.0, curve_type="cosine", curve_strength=2.0,
                   direction="right_dense")


curve_labels = {
    "線形": "linear",
    "べき関数": "power",
    "余弦": "cosine",
    "指数関数": "exponential",
}

direction_labels = {
    "右に向かって密": "right_dense",
    "左に向かって密": "left_dense",
    "中央に向かって密": "center_dense",
    "両端に向かって密": "edge_dense",
}

reverse_curve_labels = {v: k for k, v in curve_labels.items()}
reverse_direction_labels = {v: k for k, v in direction_labels.items()}


# --------------------------
# Input form
# --------------------------
with st.form("shoji_form"):
    st.subheader("パネル寸法")

    col1, col2 = st.columns(2)
    with col1:
        panel_width = st.number_input(
            "有効幅 W [mm]",
            min_value=10.0,
            max_value=5000.0,
            value=float(default["panel_width"]),
            step=1.0,
            format="%.1f",
        )
    with col2:
        panel_height = st.number_input(
            "有効高さ H [mm]",
            min_value=10.0,
            max_value=5000.0,
            value=float(default["panel_height"]),
            step=1.0,
            format="%.1f",
        )

    st.subheader("組子寸法")

    col3, col4 = st.columns(2)
    with col3:
        bar_width = st.number_input(
            "組子幅 [mm]",
            min_value=0.1,
            max_value=200.0,
            value=float(default["bar_width"]),
            step=0.1,
            format="%.1f",
        )
    with col4:
        bar_thickness = st.number_input(
            "組子厚み [mm]",
            min_value=0.1,
            max_value=200.0,
            value=float(default["bar_thickness"]),
            step=0.1,
            format="%.1f",
        )

    col5, col6 = st.columns(2)
    with col5:
        bar_count = st.number_input(
            "組子本数",
            min_value=1,
            max_value=300,
            value=int(default["bar_count"]),
            step=1,
        )
    with col6:
        bar_length_mode = st.radio(
            "組子長さ",
            ["高さと同じ", "指定する"],
            horizontal=True,
        )

    if bar_length_mode == "指定する":
        bar_length = st.number_input(
            "組子長さ [mm]",
            min_value=1.0,
            max_value=5000.0,
            value=float(panel_height),
            step=1.0,
            format="%.1f",
        )
    else:
        bar_length = None

    st.subheader("ピッチ変化")

    curve_type_label = st.selectbox(
        "曲線タイプ",
        list(curve_labels.keys()),
        index=list(curve_labels.keys()).index(reverse_curve_labels[default["curve_type"]]),
    )

    direction_label = st.selectbox(
        "密になる方向",
        list(direction_labels.keys()),
        index=list(direction_labels.keys()).index(reverse_direction_labels[default["direction"]]),
    )

    variation_percent = st.slider(
        "変化率 [%]",
        min_value=0,
        max_value=95,
        value=int(default["variation_percent"]),
        step=1,
    )

    curve_strength = st.slider(
        "曲線の強さ",
        min_value=0.2,
        max_value=6.0,
        value=float(default["curve_strength"]),
        step=0.1,
    )

    show_gap_labels = st.checkbox("PNGに隙間寸法を表示", value=True)

    submitted = st.form_submit_button("PNGを生成")


# --------------------------
# Generate
# --------------------------
if submitted:
    params = ShojiPanelParams(
        panel_width=float(panel_width),
        panel_height=float(panel_height),
        bar_width=float(bar_width),
        bar_thickness=float(bar_thickness),
        bar_length=None if bar_length is None else float(bar_length),
        bar_count=int(bar_count),
        variation_percent=float(variation_percent),
        curve_type=curve_labels[curve_type_label],
        curve_strength=float(curve_strength),
        direction=direction_labels[direction_label],
        show_gap_labels=bool(show_gap_labels),
    )

    try:
        bars_df, gaps_df, summary = calculate_shoji_panel(params)
    except Exception as e:
        st.error("この条件では計算できません。")
        st.warning(str(e))
        st.stop()

    output_dir = Path("output")
    output_dir.mkdir(exist_ok=True)
    run_id = uuid.uuid4().hex[:8]

    png_path = output_dir / f"shoji_panel_{run_id}.png"
    bars_csv_path = output_dir / f"shoji_panel_{run_id}_bars.csv"
    gaps_csv_path = output_dir / f"shoji_panel_{run_id}_gaps.csv"
    summary_csv_path = output_dir / f"shoji_panel_{run_id}_summary.csv"

    try:
        plot_shoji_panel(
            bars_df,
            gaps_df,
            summary,
            png_path,
            show_gap_labels=show_gap_labels,
        )
    except Exception as e:
        st.error("PNG生成中にエラーが出ました。")
        st.code(repr(e))
        st.stop()

    bars_df.round(2).to_csv(bars_csv_path, index=False, encoding="utf-8-sig")
    gaps_df.round(2).to_csv(gaps_csv_path, index=False, encoding="utf-8-sig")
    pd.DataFrame([summary]).round(2).to_csv(summary_csv_path, index=False, encoding="utf-8-sig")

    st.success("生成できました。")

    c1, c2, c3 = st.columns(3)
    with c1:
        st.metric("最小隙間", f"{summary['min_gap_mm']:.1f} mm")
    with c2:
        st.metric("最大隙間", f"{summary['max_gap_mm']:.1f} mm")
    with c3:
        st.metric("隙間比", f"{summary['min_max_gap_ratio']:.2f}")

    st.image(str(png_path), caption="生成された障子ピッチ図", use_container_width=True)

    with st.expander("隙間寸法表"):
        st.dataframe(gaps_df.round(2), use_container_width=True, hide_index=True)

    with st.expander("組子位置表"):
        st.dataframe(bars_df.round(2), use_container_width=True, hide_index=True)

    with st.expander("ダウンロード"):
        with open(png_path, "rb") as f:
            st.download_button("PNGを保存", f, file_name=png_path.name, mime="image/png")

        with open(gaps_csv_path, "rb") as f:
            st.download_button("隙間寸法CSV", f, file_name=gaps_csv_path.name, mime="text/csv")

        with open(bars_csv_path, "rb") as f:
            st.download_button("組子位置CSV", f, file_name=bars_csv_path.name, mime="text/csv")

        with open(summary_csv_path, "rb") as f:
            st.download_button("サマリーCSV", f, file_name=summary_csv_path.name, mime="text/csv")
