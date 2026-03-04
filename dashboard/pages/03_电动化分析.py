"""Page 3: 电动化分析 — BEV 深挖 + 电驱桥 + 电池"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import streamlit as st
from dashboard.sidebar import apply_sidebar_filters, _load
from src.analysis.energy import (
    bev_trend, bev_vehicle_types, bev_motor_suppliers, bev_power_distribution,
    battery_chemistry_trend, battery_chemistry_distribution,
    battery_cell_suppliers, battery_pack_suppliers, battery_capacity_stats,
)
from src.analysis.edrive import (
    drive_topology_distribution, drive_topology_trend, eaxle_supplier_share,
    tz_number_vs_power, tz_maker_code_distribution, eaxle_trend, bev_by_mass_class,
)
from src.charts import (
    dual_axis_chart, pie_chart, bar_h, area_chart, scatter_chart,
    line_chart, grouped_bar, ZF_BLUE, ZF_COLORS,
)

st.set_page_config(page_title="电动化分析", layout="wide")
st.markdown("# 🔋 电动化分析 Electrification")

df_f = apply_sidebar_filters(default_batch_window=24)

if len(df_f) == 0:
    st.warning("当前筛选条件下无数据")
    st.stop()

df_full = _load()
seg_cats = df_f["vehicle_category"].unique().tolist()
df_trend = df_full[df_full["vehicle_category"].isin(seg_cats)]
b_min, b_max = int(df_f["batch"].min()), int(df_f["batch"].max())

# ── BEV 趋势 ──
st.subheader("新能源车型占比趋势")
bev_df = bev_trend(df_trend)
bev_range = bev_df[bev_df["batch"].between(b_min, b_max)]
fig = dual_axis_chart(bev_range, x="batch_date", y1="bev", y2="nev_ratio",
                      y1_name="BEV 数量", y2_name="NEV 总占比", height=380)
fig.update_layout(yaxis2_tickformat=".0%")
st.plotly_chart(fig, use_container_width=True)

# ── BEV 车辆类型 + 电机供应商 ──
col1, col2 = st.columns(2)
with col1:
    st.subheader("BEV 车辆大类分布")
    vt = bev_vehicle_types(df_f)
    fig = pie_chart(vt, names="vehicle_category", values="count", height=380)
    st.plotly_chart(fig, use_container_width=True)

with col2:
    st.subheader("BEV 电机供应商 Top 15")
    ms = bev_motor_suppliers(df_f, 15)
    fig = bar_h(ms, x="count", y="supplier", height=420)
    st.plotly_chart(fig, use_container_width=True)

# ── 电驱桥 vs 集中驱动 ──
st.markdown("---")
st.subheader("⚡ 电驱拓扑分析 (参考性分析)")
st.caption("基于 engine_maker 企业属性推断，非公告官方分类")

col3, col4 = st.columns(2)
with col3:
    topo = drive_topology_distribution(df_f)
    fig = pie_chart(topo, names="topology", values="count", title="BEV 驱动拓扑分布", height=350)
    st.plotly_chart(fig, use_container_width=True)

with col4:
    ea_trend = eaxle_trend(df_trend)
    ea_range = ea_trend[ea_trend["batch"].between(b_min, b_max)]
    fig = dual_axis_chart(ea_range, x="batch_date", y1="eaxle_count", y2="eaxle_ratio",
                          y1_name="电驱桥数量", y2_name="占BEV比例", title="电驱桥趋势", height=350)
    fig.update_layout(yaxis2_tickformat=".1%")
    st.plotly_chart(fig, use_container_width=True)

col5, col6 = st.columns(2)
with col5:
    st.subheader("电驱桥供应商格局")
    eas = eaxle_supplier_share(df_f)
    if len(eas) > 0:
        fig = bar_h(eas, x="count", y="supplier", height=350)
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("所选批次无电驱桥数据")

with col6:
    st.subheader("TZ型号数字 vs 功率 (kW)")
    tz_data = tz_number_vs_power(df_f)
    if len(tz_data) > 0:
        fig = scatter_chart(tz_data, x="parsed_tz_number", y="power_kw",
                            color="parsed_tz_suffix_type", height=350)
        fig.update_layout(xaxis_title="TZ型号数字", yaxis_title="功率 (kW)")
        st.plotly_chart(fig, use_container_width=True)

# ── 推断逻辑说明 + 声明 ──
with st.expander("📖 查看电驱拓扑推断逻辑与准确性声明", expanded=False):
    st.markdown("""
### 推断逻辑

中国商用车公告数据中 **没有** "电驱桥" 或 "集中驱动" 的官方字段。本平台通过分析
BEV 车型的 `engine_maker`（发动机/电机生产企业）名称中的关键词，**启发式地推断** 驱动拓扑类型。

**分类规则如下：**

| 分类结果 | 判定条件 | 关键词 |
|----------|----------|--------|
| **电驱桥 (参考)** | `engine_maker` 包含车桥类企业关键词 | `车桥`、`桥有限`、`法士特齿轮`、`德纳` |
| **OEM自研 (参考)** | `engine_maker` 全部匹配 OEM 整车企业关键词 | `汽车股份`、`客车`、`汽车有限`、`汽车制造`、`比亚迪`、`吉利`、`蔚来`、`小鹏` |
| **集中驱动 (参考)** | 以上条件均不满足时的 **默认分类** | — |
| **未知** | BEV 车型但 `engine_maker` 为空 | — |

**TZ 型号解析规则：**
- 从 `engine_model` 字段中提取 `TZ{数字}` 格式的电机型号
- 数字部分通常与电机的额定扭矩或功率等级相关（如 TZ200 通常对应 200 Nm 等级）
- 后缀字母可能代表产品系列变体（如 A/B/C/X 等）
- TZ 前缀代码（如 HD、DN、SZF 等）对应不同的电机制造商
""")

    st.warning("""
**⚠️ 准确性声明 — 请务必阅读**

以上电驱拓扑分类结果 **仅供参考，不可作为正式商业决策依据**。已知局限包括：

1. **企业多产品线**：部分电机企业同时生产电驱桥和集中驱动产品，仅凭企业名称无法区分具体产品形态；
2. **关键词覆盖不全**：新进入市场的电驱桥企业可能未被当前关键词列表覆盖，导致被错误归类为"集中驱动"；
3. **申报名义差异**：OEM 可能使用第三方供应商的电驱桥产品，但以自有名义申报公告，导致被归类为"OEM自研"；
4. **默认分类偏差**："集中驱动"是默认兜底分类，可能包含实际为电驱桥但未被识别的车型；
5. **数据源限制**：公告数据的 `engine_maker` 字段本身可能存在填写不规范的情况。

如需更准确的电驱桥市场分析，建议结合实际产品目录和供应商确认进行人工校验。
""")

# ── 电池分析 ──
st.markdown("---")
st.subheader("🔋 电池技术分析")

col7, col8 = st.columns(2)
with col7:
    bc = battery_chemistry_distribution(df_f)
    fig = pie_chart(bc, names="chemistry", values="count", title="电池化学类型分布", height=350)
    st.plotly_chart(fig, use_container_width=True)

with col8:
    bc_trend = battery_chemistry_trend(df_trend)
    bc_range = bc_trend[bc_trend["batch"].between(b_min, b_max)]
    known = bc_range[bc_range["parsed_battery_chemistry"] != "未知"]
    fig = area_chart(known, x="batch_date", y="count", color="parsed_battery_chemistry",
                     title="电池化学类型趋势 (已标注)", height=350)
    st.plotly_chart(fig, use_container_width=True)

col9, col10 = st.columns(2)
with col9:
    st.subheader("电芯供应商 Top 10")
    bcs = battery_cell_suppliers(df_f, 10)
    if len(bcs) > 0:
        fig = bar_h(bcs, x="count", y="display", height=380)
        st.plotly_chart(fig, use_container_width=True)

with col10:
    st.subheader("电池包供应商 Top 10")
    bps = battery_pack_suppliers(df_f, 10)
    if len(bps) > 0:
        fig = bar_h(bps, x="count", y="display", height=380)
        st.plotly_chart(fig, use_container_width=True)

# ── BEV 质量段分析 ──
st.markdown("---")
st.subheader("BEV 质量段趋势")
bev_mass = bev_by_mass_class(df_trend)
bev_mass_range = bev_mass[bev_mass["batch"].between(b_min, b_max)]
fig = area_chart(bev_mass_range, x="batch_date", y="count", color="mass_class",
                 title="BEV 各质量段车型数量", height=380)
st.plotly_chart(fig, use_container_width=True)
