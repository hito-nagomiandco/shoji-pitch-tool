#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Shoji panel pitch calculator

A small calculation engine for a single shoji sub-panel.
It generates:
- bar positions
- gap dimensions
- visual PNG
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Literal

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle


@dataclass
class ShojiPanelParams:
    panel_width: float = 360.0
    panel_height: float = 600.0
    bar_width: float = 5.0
    bar_thickness: float = 12.0
    bar_length: float | None = None
    bar_count: int = 18
    variation_percent: float = 70.0
    curve_type: Literal["linear", "power", "cosine", "exponential"] = "cosine"
    curve_strength: float = 2.0
    direction: Literal["right_dense", "left_dense", "center_dense", "edge_dense"] = "right_dense"
    show_gap_labels: bool = True


def normalize01(x: np.ndarray) -> np.ndarray:
    mn = float(np.min(x))
    mx = float(np.max(x))
    if abs(mx - mn) < 1e-12:
        return np.zeros_like(x)
    return (x - mn) / (mx - mn)


def curve_profile(u: np.ndarray, curve_type: str, curve_strength: float) -> np.ndarray:
    u = np.asarray(u, dtype=float)

    if curve_type == "linear":
        y = u

    elif curve_type == "power":
        k = max(float(curve_strength), 0.01)
        y = u ** k

    elif curve_type == "cosine":
        # Smooth and visually natural
        y = 0.5 - 0.5 * np.cos(np.pi * u)
        k = max(float(curve_strength), 0.01)
        if abs(k - 1.0) > 1e-9:
            y = y ** (1.0 / k)

    elif curve_type == "exponential":
        k = max(float(curve_strength), 0.01)
        y = (np.exp(k * u) - 1.0) / (np.exp(k) - 1.0)

    else:
        raise ValueError(f"Unsupported curve_type: {curve_type}")

    return normalize01(y)


def make_gap_weights(gap_count: int, params: ShojiPanelParams) -> np.ndarray:
    if gap_count < 2:
        return np.ones(gap_count)

    u = np.linspace(0.0, 1.0, gap_count)

    # 0% = equal spacing, 95% = very strong contrast
    variation = min(max(float(params.variation_percent), 0.0), 95.0)
    min_ratio = 1.0 - variation / 100.0

    if params.direction in ["right_dense", "left_dense"]:
        p = curve_profile(u, params.curve_type, params.curve_strength)

        if params.direction == "right_dense":
            # wide on left, dense on right
            weights = 1.0 - (1.0 - min_ratio) * p
        else:
            # dense on left, wide on right
            weights = min_ratio + (1.0 - min_ratio) * p

    elif params.direction == "center_dense":
        # dense near center, wide near edges
        edge_profile = np.abs(2.0 * u - 1.0)
        k = max(float(params.curve_strength), 0.01)
        weights = min_ratio + (1.0 - min_ratio) * (edge_profile ** k)

    elif params.direction == "edge_dense":
        # dense near edges, wide near center
        center_profile = 1.0 - np.abs(2.0 * u - 1.0)
        k = max(float(params.curve_strength), 0.01)
        weights = min_ratio + (1.0 - min_ratio) * (center_profile ** k)

    else:
        raise ValueError(f"Unsupported direction: {params.direction}")

    return np.maximum(weights, 1e-9)


def calculate_shoji_panel(params: ShojiPanelParams):
    W = float(params.panel_width)
    H = float(params.panel_height)
    b = float(params.bar_width)
    N = int(params.bar_count)

    if params.bar_length is None:
        bar_length = H
    else:
        bar_length = float(params.bar_length)

    if W <= 0 or H <= 0:
        raise ValueError("Panel width and height must be positive.")

    if N <= 0:
        raise ValueError("Bar count must be 1 or more.")

    if b <= 0:
        raise ValueError("Bar width must be positive.")

    total_bar_width = N * b
    total_gap_width = W - total_bar_width

    if total_gap_width <= 0:
        raise ValueError(
            f"Panel width is too small. panel_width={W:.2f}, bar_count*bar_width={total_bar_width:.2f}"
        )

    gap_count = N + 1
    weights = make_gap_weights(gap_count, params)
    gaps = total_gap_width * weights / np.sum(weights)

    bars = []
    x = gaps[0]

    for i in range(N):
        x_left = x
        x_right = x_left + b
        x_center = (x_left + x_right) / 2.0

        bars.append({
            "bar_no": i + 1,
            "x_left_mm": x_left,
            "x_center_mm": x_center,
            "x_right_mm": x_right,
            "bar_width_mm": b,
            "bar_thickness_mm": float(params.bar_thickness),
            "bar_length_mm": bar_length,
        })

        if i < N - 1:
            x = x_right + gaps[i + 1]

    gap_rows = []
    for i, g in enumerate(gaps):
        if i == 0:
            name = "left_edge_gap"
            between = "left_frame - bar_1"
        elif i == gap_count - 1:
            name = "right_edge_gap"
            between = f"bar_{N} - right_frame"
        else:
            name = f"gap_{i}"
            between = f"bar_{i} - bar_{i+1}"

        gap_rows.append({
            "gap_no": i,
            "gap_name": name,
            "between": between,
            "gap_mm": g,
        })

    bars_df = pd.DataFrame(bars)
    gaps_df = pd.DataFrame(gap_rows)

    summary = {
        "panel_width_mm": W,
        "panel_height_mm": H,
        "bar_count": N,
        "bar_width_mm": b,
        "bar_thickness_mm": float(params.bar_thickness),
        "bar_length_mm": bar_length,
        "total_bar_width_mm": total_bar_width,
        "total_gap_width_mm": total_gap_width,
        "min_gap_mm": float(np.min(gaps)),
        "max_gap_mm": float(np.max(gaps)),
        "min_max_gap_ratio": float(np.min(gaps) / np.max(gaps)),
        "curve_type": params.curve_type,
        "curve_strength": float(params.curve_strength),
        "variation_percent": float(params.variation_percent),
        "direction": params.direction,
    }

    return bars_df, gaps_df, summary


def draw_dimension_arrow(ax, x1, x2, y, text, fs=7.5, color="black"):
    ax.annotate(
        "",
        xy=(x2, y),
        xytext=(x1, y),
        arrowprops=dict(arrowstyle="<->", lw=0.65, color=color, shrinkA=0, shrinkB=0),
    )
    ax.text(
        (x1 + x2) / 2.0,
        y,
        text,
        fontsize=fs,
        ha="center",
        va="center",
        bbox=dict(boxstyle="round,pad=0.08", facecolor="white", edgecolor="none"),
        color=color,
    )


def plot_shoji_panel(
    bars_df: pd.DataFrame,
    gaps_df: pd.DataFrame,
    summary: dict,
    out_png: str | Path,
    show_gap_labels: bool = True,
) -> None:
    W = summary["panel_width_mm"]
    H = summary["panel_height_mm"]

    # Wider than tall, because it represents one horizontal sub-panel.
    fig, ax = plt.subplots(figsize=(8.0, 5.2), facecolor="white")

    # Panel background
    ax.add_patch(Rectangle((0, 0), W, H, facecolor="#fff8e7", edgecolor="black", linewidth=1.2))

    # Vertical kumiko bars
    for _, row in bars_df.iterrows():
        ax.add_patch(
            Rectangle(
                (row["x_left_mm"], 0),
                row["bar_width_mm"],
                H,
                facecolor="#a87536",
                edgecolor="black",
                linewidth=0.55,
            )
        )

    # Gap labels
    if show_gap_labels:
        y_dim = -H * 0.07
        for _, g in gaps_df.iterrows():
            gap_no = int(g["gap_no"])
            gap_val = float(g["gap_mm"])

            if gap_no == 0:
                x1 = 0.0
                x2 = float(bars_df.iloc[0]["x_left_mm"])
            elif gap_no == len(gaps_df) - 1:
                x1 = float(bars_df.iloc[-1]["x_right_mm"])
                x2 = W
            else:
                x1 = float(bars_df.iloc[gap_no - 1]["x_right_mm"])
                x2 = float(bars_df.iloc[gap_no]["x_left_mm"])

            fs = 6.6 if len(gaps_df) > 16 else 7.5
            draw_dimension_arrow(ax, x1, x2, y_dim, f"{gap_val:.1f}", fs=fs)

    # Overall width
    draw_dimension_arrow(ax, 0, W, -H * 0.16, f"W = {W:.1f} mm", fs=9)

    info = (
        f"N={summary['bar_count']}  bar={summary['bar_width_mm']:.1f}mm  "
        f"min={summary['min_gap_mm']:.1f}  max={summary['max_gap_mm']:.1f}  "
        f"{summary['curve_type']} / {summary['direction']} / {summary['variation_percent']:.0f}%"
    )
    ax.text(0, H + H * 0.05, info, fontsize=9, ha="left", va="bottom")

    ax.set_aspect("equal", adjustable="box")
    ax.axis("off")

    margin_x = W * 0.03
    ax.set_xlim(-margin_x, W + margin_x)
    ax.set_ylim(-H * 0.23, H * 1.13)

    fig.savefig(out_png, dpi=300, bbox_inches="tight", facecolor="white")
    plt.close(fig)
