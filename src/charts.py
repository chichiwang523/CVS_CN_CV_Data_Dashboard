"""Plotly 图表工厂 — ZF 企业蓝色主题统一风格"""
from __future__ import annotations
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
from src.config import ZF_BLUE, ZF_COLORS, PLOTLY_LAYOUT


def _apply_layout(fig, title: str = "", height: int = 400):
    fig.update_layout(**PLOTLY_LAYOUT, title=dict(text=title, font_size=16), height=height)
    return fig


def kpi_card_html(label: str, value, delta: str = "", color: str = ZF_BLUE) -> str:
    delta_html = ""
    if delta:
        arrow = "▲" if not delta.startswith("-") else "▼"
        d_color = "#2A9D8F" if not delta.startswith("-") else "#E63946"
        delta_html = f'<span style="color:{d_color};font-size:14px;">{arrow} {delta}</span>'
    return f"""
    <div style="background:white;border-left:4px solid {color};padding:16px 20px;
                border-radius:4px;box-shadow:0 1px 3px rgba(0,0,0,0.1);text-align:center;">
        <div style="color:#666;font-size:13px;margin-bottom:4px;">{label}</div>
        <div style="color:{color};font-size:28px;font-weight:700;">{value}</div>
        {delta_html}
    </div>"""


def pie_chart(df: pd.DataFrame, names: str, values: str, title: str = "", height: int = 380) -> go.Figure:
    fig = px.pie(df, names=names, values=values, color_discrete_sequence=ZF_COLORS, hole=0.35)
    fig.update_traces(textposition="outside", textinfo="label+percent")
    return _apply_layout(fig, title, height)


def bar_h(df: pd.DataFrame, x: str, y: str, title: str = "", height: int = 400, color: str = ZF_BLUE) -> go.Figure:
    fig = px.bar(df, x=x, y=y, orientation="h", color_discrete_sequence=[color])
    fig.update_layout(yaxis=dict(autorange="reversed"))
    return _apply_layout(fig, title, height)


def bar_v(df: pd.DataFrame, x: str, y: str, title: str = "", height: int = 400, color: str = ZF_BLUE) -> go.Figure:
    fig = px.bar(df, x=x, y=y, color_discrete_sequence=[color])
    return _apply_layout(fig, title, height)


def line_chart(df: pd.DataFrame, x: str, y: str, color: str | None = None,
               title: str = "", height: int = 400) -> go.Figure:
    fig = px.line(df, x=x, y=y, color=color, color_discrete_sequence=ZF_COLORS, markers=True)
    return _apply_layout(fig, title, height)


def area_chart(df: pd.DataFrame, x: str, y: str, color: str,
               title: str = "", height: int = 400) -> go.Figure:
    fig = px.area(df, x=x, y=y, color=color, color_discrete_sequence=ZF_COLORS)
    return _apply_layout(fig, title, height)


def scatter_chart(df: pd.DataFrame, x: str, y: str, color: str | None = None,
                  title: str = "", height: int = 400) -> go.Figure:
    fig = px.scatter(df, x=x, y=y, color=color, color_discrete_sequence=ZF_COLORS, opacity=0.6)
    return _apply_layout(fig, title, height)


def grouped_bar(df: pd.DataFrame, x: str, y: str, color: str,
                title: str = "", height: int = 400, barmode: str = "group") -> go.Figure:
    fig = px.bar(df, x=x, y=y, color=color, barmode=barmode, color_discrete_sequence=ZF_COLORS)
    return _apply_layout(fig, title, height)


def dual_axis_chart(df: pd.DataFrame, x: str, y1: str, y2: str,
                    y1_name: str = "", y2_name: str = "",
                    title: str = "", height: int = 400) -> go.Figure:
    fig = go.Figure()
    fig.add_trace(go.Bar(x=df[x], y=df[y1], name=y1_name or y1,
                         marker_color=ZF_BLUE, opacity=0.7))
    fig.add_trace(go.Scatter(x=df[x], y=df[y2], name=y2_name or y2,
                             yaxis="y2", mode="lines+markers",
                             line=dict(color="#E63946", width=2)))
    fig.update_layout(
        **PLOTLY_LAYOUT,
        title=dict(text=title, font_size=16),
        height=height,
        yaxis=dict(title=y1_name or y1),
        yaxis2=dict(title=y2_name or y2, overlaying="y", side="right", showgrid=False),
    )
    return fig
