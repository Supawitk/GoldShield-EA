#!/usr/bin/env python3
"""Generate architecture diagram PNGs for the README."""

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
import numpy as np


def draw_rounded_box(ax, x, y, w, h, label, sublabel=None, color="#1a1a2e",
                     edge="#00d2ff", text_color="white", fontsize=11, icon=None):
    """Draw a styled rounded rectangle with label."""
    box = FancyBboxPatch(
        (x, y), w, h,
        boxstyle="round,pad=0.15",
        facecolor=color, edgecolor=edge, linewidth=2,
        alpha=0.95, zorder=2
    )
    ax.add_patch(box)

    ty = y + h / 2 + (0.12 if sublabel else 0)
    prefix = f"{icon}  " if icon else ""
    ax.text(x + w / 2, ty, f"{prefix}{label}",
            ha="center", va="center", fontsize=fontsize,
            fontweight="bold", color=text_color, zorder=3)

    if sublabel:
        ax.text(x + w / 2, y + h / 2 - 0.18, sublabel,
                ha="center", va="center", fontsize=8,
                color="#aaaaaa", zorder=3, style="italic")


def draw_arrow(ax, x1, y1, x2, y2, color="#00d2ff"):
    """Draw a curved arrow between two points."""
    ax.annotate("", xy=(x2, y2), xytext=(x1, y1),
                arrowprops=dict(
                    arrowstyle="-|>",
                    color=color, lw=2,
                    connectionstyle="arc3,rad=0.05"
                ), zorder=1)


def generate_architecture():
    """Main architecture diagram."""
    fig, ax = plt.subplots(1, 1, figsize=(14, 7))
    fig.patch.set_facecolor("#0d1117")
    ax.set_facecolor("#0d1117")
    ax.set_xlim(-0.5, 13.5)
    ax.set_ylim(-0.5, 7)
    ax.axis("off")

    # Title
    ax.text(6.75, 6.5, "GoldShield EA — System Architecture",
            ha="center", va="center", fontsize=18, fontweight="bold",
            color="white", zorder=3)

    # Row 1: Main pipeline
    draw_rounded_box(ax, 0, 3.8, 2.8, 1.8, "MetaTrader 5", "GoldShield EA.mq5",
                     color="#1e3a5f", edge="#4da8da")
    draw_rounded_box(ax, 4, 3.8, 3.2, 1.8, "PostgreSQL 16",
                     "TimescaleDB + pgvector",
                     color="#1a3a1a", edge="#2ea043")
    draw_rounded_box(ax, 8.5, 3.8, 2.5, 1.8, "MCP Server",
                     "6 AI-ready tools",
                     color="#3a1a3a", edge="#bc4dff")
    draw_rounded_box(ax, 11.5, 3.8, 2.0, 1.8, "AI Client",
                     "Claude / Any LLM",
                     color="#3a2a1a", edge="#ff9f43")

    # Arrows row 1
    draw_arrow(ax, 2.8, 4.7, 4.0, 4.7, "#4da8da")
    draw_arrow(ax, 7.2, 4.7, 8.5, 4.7, "#2ea043")
    draw_arrow(ax, 11.0, 4.7, 11.5, 4.7, "#bc4dff")

    # Row 2: Data sources
    draw_rounded_box(ax, 0, 1.2, 2.8, 1.5, "Market Data API",
                     "Twelve Data / MetaAPI",
                     color="#1a2a3a", edge="#00b4d8")
    draw_rounded_box(ax, 4, 1.2, 3.2, 1.5, "ML Models",
                     "Python sklearn + R",
                     color="#2a1a1a", edge="#e74c3c")
    draw_rounded_box(ax, 8.5, 1.2, 2.5, 1.5, "Dashboard",
                     "Streamlit UI",
                     color="#1a2a2a", edge="#00cec9")

    # Arrows to DB
    draw_arrow(ax, 1.4, 2.7, 4.8, 3.8, "#00b4d8")
    draw_arrow(ax, 5.6, 2.7, 5.6, 3.8, "#e74c3c")
    draw_arrow(ax, 9.75, 2.7, 6.5, 3.8, "#00cec9")

    # Feedback arrow from AI back to EA
    ax.annotate("", xy=(1.4, 5.6), xytext=(12.5, 5.6),
                arrowprops=dict(
                    arrowstyle="-|>",
                    color="#ff9f43", lw=1.5, ls="--",
                    connectionstyle="arc3,rad=-0.25"
                ), zorder=1)
    ax.text(6.75, 6.05, "Parameter Adjustments",
            ha="center", va="center", fontsize=9,
            color="#ff9f43", style="italic", zorder=3)

    # DB detail labels
    labels = ["candles", "trades", "parameters", "embeddings"]
    colors = ["#2ea043", "#4da8da", "#bc4dff", "#e74c3c"]
    for i, (lbl, c) in enumerate(zip(labels, colors)):
        bx = 4.2 + i * 0.75
        ax.add_patch(FancyBboxPatch(
            (bx, 4.05), 0.7, 0.35,
            boxstyle="round,pad=0.05",
            facecolor=c, edgecolor="none", alpha=0.3, zorder=2
        ))
        ax.text(bx + 0.35, 4.22, lbl, ha="center", va="center",
                fontsize=7, color="white", zorder=3)

    plt.tight_layout(pad=0.5)
    fig.savefig("/Users/admin/Downloads/EA-v1.0/assets/architecture.png",
                dpi=200, facecolor=fig.get_facecolor(),
                bbox_inches="tight", pad_inches=0.3)
    plt.close()
    print("Generated: architecture.png")


def generate_dataflow():
    """Data flow diagram."""
    fig, ax = plt.subplots(1, 1, figsize=(10, 8))
    fig.patch.set_facecolor("#0d1117")
    ax.set_facecolor("#0d1117")
    ax.set_xlim(-0.5, 9.5)
    ax.set_ylim(-0.5, 8.5)
    ax.axis("off")

    ax.text(4.75, 8.0, "Data Flow Pipeline",
            ha="center", va="center", fontsize=16, fontweight="bold",
            color="white")

    # Vertical flow
    steps = [
        (1.5, 6.5, 2.5, 1.0, "Market Data API", "XAUUSD OHLCV", "#1a2a3a", "#00b4d8"),
        (5.5, 6.5, 2.5, 1.0, "MT5 Backtest", "HTML Reports", "#1e3a5f", "#4da8da"),
        (3.0, 4.5, 3.5, 1.2, "PostgreSQL", "TimescaleDB + pgvector\n4 hypertables", "#1a3a1a", "#2ea043"),
        (3.0, 2.5, 3.5, 1.0, "MCP Server", "query / analyse / suggest", "#3a1a3a", "#bc4dff"),
        (3.0, 0.5, 3.5, 1.0, "AI Analysis", "Parameter optimization", "#3a2a1a", "#ff9f43"),
    ]

    for x, y, w, h, label, sub, color, edge in steps:
        draw_rounded_box(ax, x, y, w, h, label, sub, color, edge)

    # Arrows
    draw_arrow(ax, 2.75, 6.5, 4.0, 5.7, "#00b4d8")
    draw_arrow(ax, 6.75, 6.5, 5.5, 5.7, "#4da8da")
    draw_arrow(ax, 4.75, 4.5, 4.75, 3.5, "#2ea043")
    draw_arrow(ax, 4.75, 2.5, 4.75, 1.5, "#bc4dff")

    # Feedback arrow
    ax.annotate("", xy=(7.0, 7.0), xytext=(7.0, 1.0),
                arrowprops=dict(
                    arrowstyle="-|>",
                    color="#ff9f43", lw=1.5, ls="--",
                    connectionstyle="arc3,rad=-0.4"
                ), zorder=1)
    ax.text(8.2, 4.0, "Feedback\nLoop",
            ha="center", va="center", fontsize=9,
            color="#ff9f43", style="italic")

    plt.tight_layout(pad=0.5)
    fig.savefig("/Users/admin/Downloads/EA-v1.0/assets/dataflow.png",
                dpi=200, facecolor=fig.get_facecolor(),
                bbox_inches="tight", pad_inches=0.3)
    plt.close()
    print("Generated: dataflow.png")


if __name__ == "__main__":
    generate_architecture()
    generate_dataflow()
