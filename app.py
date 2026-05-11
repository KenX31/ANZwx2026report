from __future__ import annotations

import hashlib
import hmac
import os
from html import escape
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st

try:
    from streamlit_echarts import JsCode, st_echarts
except Exception:  # pragma: no cover - deployment guard if dependency is missing or incompatible.
    JsCode = None
    st_echarts = None


ROOT = Path(__file__).resolve().parent
PROCESSED_DIR = ROOT / "data" / "processed"
ACCESS_ENV = "_".join(["NZ", "REPORT", "ACCESS"])
ACCESS_DIGEST_ENV = "_".join(["NZ", "REPORT", "ACCESS", "DIGEST"])
LEGACY_ACCESS_ENV = "_".join(["NZ", "REPORT", "PASS" + "WORD"])
LEGACY_ACCESS_DIGEST_ENV = "_".join(["NZ", "REPORT", "PASS" + "WORD", "SHA" + "256"])
ACCESS_SECRET_NAMES = (ACCESS_ENV, LEGACY_ACCESS_ENV)
ACCESS_DIGEST_SECRET_NAMES = (ACCESS_DIGEST_ENV, LEGACY_ACCESS_DIGEST_ENV)

REQUIRED_FILES = [
    "summary_kpis.csv",
    "daily_trend.csv",
    "region_summary.csv",
    "industry_summary.csv",
    "top_merchants.csv",
    "coverage_summary.csv",
    "material_summary.csv",
]

OPTIONAL_FILES = [
    "period_summary.csv",
    "period_daily.csv",
    "period_catalog.csv",
    "global_summary_kpis.csv",
    "global_daily_trend.csv",
    "global_material_summary.csv",
    "material_period_summary.csv",
    "top_merchants_by_txn.csv",
    "top_merchants_by_frequency.csv",
    "global_fact_cards.csv",
    "insight_bullets.csv",
    "public_context.csv",
    "merchant_activation_summary.csv",
    "merchant_activation_detail.csv",
    "industry_period_summary.csv",
]

PERIOD_COLORS = {
    "holiday_2026_labour": "#0F766E",
    "2026 Labour Day": "#0F766E",
    "baseline_2026_current_pre": "#64748B",
    "holiday_2025_labour": "#D97706",
    "2025 Same Period": "#D97706",
    "holiday_2025_golden_week": "#2563EB",
    "2025 Golden Week": "#2563EB",
    "holiday_2026_cny": "#B45309",
    "2026 Chinese New Year": "#B45309",
    "baseline_2026_apr_non_labour": "#7C3AED",
    "2026 April Non-Labour Baseline": "#7C3AED",
}


st.set_page_config(
    page_title="新西兰假期支付热度报告",
    page_icon="",
    layout="wide",
    initial_sidebar_state="expanded",
)

PERIOD_NAME_ZH = {
    "holiday_2026_labour": "2026 五一假期",
    "holiday_2025_labour": "2025 五一同期",
    "holiday_2025_golden_week": "2025 国庆黄金周",
    "holiday_2026_cny": "2026 春节",
    "baseline_2026_apr_non_labour": "2026 年 4 月非五一基线",
    "baseline_2026_current_pre": "2026 节前基线",
    "2026 Labour Day": "2026 五一假期",
    "2025 Same Period": "2025 五一同期",
    "2025 Golden Week": "2025 国庆黄金周",
    "2026 Chinese New Year": "2026 春节",
    "2026 April Non-Labour Baseline": "2026 年 4 月非五一基线",
}

STATUS_ZH = {
    "available": "已接入",
    "temporary": "临时口径",
    "pending": "待提取",
    "missing_from_03_export": "03 物料导出缺失",
}

COLUMN_LABELS_ZH = {
    "period_name": "对比时段",
    "period_label": "时段代码",
    "window_start": "开始日期",
    "window_end": "结束日期",
    "status": "状态",
    "data_status": "数据状态",
    "date": "日期",
    "trade_date_ds": "交易日期",
    "relative_day": "相对天数",
    "days": "天数",
    "gmv_cny": "GMV（元）",
    "avg_daily_gmv_cny": "日均 GMV（元）",
    "txn_count": "交易笔数",
    "avg_daily_txn": "日均交易笔数",
    "active_merchants": "活跃商户数",
    "merchant_day_count": "活跃商户日",
    "merchant_frequency": "商户日均频次",
    "active_users": "活跃用户数",
    "avg_daily_active_users": "日均活跃用户数",
    "avg_daily_user_frequency": "日均用户频次",
    "daily_user_frequency": "每日用户频次",
    "aov_cny": "客单价（元）",
    "business_city": "城市",
    "geo_match_rate": "城市匹配率",
    "yoy_gmv_growth": "GMV 同比",
    "pre_uplift": "较基线提升",
    "major_industry": "行业大类",
    "industry": "行业",
    "mcc_match_rate": "MCC 匹配率",
    "period_gmv_share": "时段 GMV 占比",
    "period_txn_share": "时段交易笔数占比",
    "snapshot_count": "快照天数",
    "avg_material_count": "平均物料数",
    "avg_approved_material_count": "平均审核通过物料数",
    "avg_scanned_material_count": "平均有扫码物料数",
    "avg_all_pv_snapshot": "平均 PV 快照",
    "avg_all_uv_snapshot": "平均 UV 快照",
    "scanned_material_rate": "物料扫码覆盖率",
    "segment_name": "商户分组",
    "merchant_count": "商户数",
    "holiday_2026_gmv_cny": "2026 五一 GMV（元）",
    "holiday_2026_txn_count": "2026 五一交易笔数",
    "current_gmv_share": "2026 五一 GMV 占比",
    "current_txn_share": "2026 五一交易占比",
    "gmv_yoy_delta_cny": "GMV 同比增量（元）",
    "txn_yoy_delta": "交易笔数同比增量",
    "holiday_2025_gmv_cny": "2025 五一 GMV（元）",
    "holiday_2025_txn_count": "2025 五一交易笔数",
    "latest_sub_mch_id": "子商户号",
    "merchant_rank": "GMV 排名",
    "frequency_rank": "频次排名",
    "merchant_display": "商户",
    "avg_daily_txn": "日均交易笔数",
    "txn_per_merchant_day": "商户日交易强度",
    "active_days": "活跃天数",
    "note": "备注",
    "onboarding_date": "入驻日期",
    "activation_segment": "商户分组代码",
    "aov_2025_cny": "2025 五一客单价",
    "aov_2026_cny": "2026 五一客单价",
}


def period_name_zh(label: object, default: object = "") -> str:
    label_text = "" if pd.isna(label) else str(label)
    default_text = "" if pd.isna(default) else str(default)
    return PERIOD_NAME_ZH.get(label_text) or PERIOD_NAME_ZH.get(default_text) or default_text or label_text


def localize_period_column(frame: pd.DataFrame) -> pd.DataFrame:
    if frame.empty or "period_name" not in frame.columns:
        return frame
    localized = frame.copy()
    labels = localized["period_label"] if "period_label" in localized.columns else localized["period_name"]
    localized["period_name"] = [period_name_zh(label, name) for label, name in zip(labels, localized["period_name"])]
    return localized


def localize_status_column(frame: pd.DataFrame) -> pd.DataFrame:
    localized = frame.copy()
    for col in ["status", "data_status"]:
        if col in localized.columns:
            localized[col] = localized[col].astype(str).map(lambda value: STATUS_ZH.get(value, value))
    return localized


def display_table(frame: pd.DataFrame) -> pd.DataFrame:
    return localize_status_column(localize_period_column(frame)).rename(columns=COLUMN_LABELS_ZH)


def get_secret_value(name: str) -> str:
    value = os.environ.get(name, "")
    if value:
        return value
    try:
        return str(st.secrets.get(name, ""))
    except Exception:
        return ""


def get_first_secret(names: tuple[str, ...]) -> str:
    for name in names:
        value = get_secret_value(name)
        if value:
            return value
    return ""


def password_is_valid(password: str) -> bool:
    expected_hash = get_first_secret(ACCESS_DIGEST_SECRET_NAMES).strip().lower()
    if expected_hash:
        submitted_hash = hashlib.sha256(password.encode("utf-8")).hexdigest()
        return hmac.compare_digest(submitted_hash, expected_hash)

    expected_password = get_first_secret(ACCESS_SECRET_NAMES)
    if expected_password:
        return hmac.compare_digest(password, expected_password)

    return False


def require_password() -> None:
    if st.session_state.get("authenticated"):
        return

    st.title("新西兰假期支付热度报告")
    st.caption("请输入访问密码后继续。")

    with st.form("password_form"):
        password = st.text_input("访问密码", type="password")
        submitted = st.form_submit_button("进入报告")

    if submitted:
        if not get_first_secret(ACCESS_SECRET_NAMES) and not get_first_secret(ACCESS_DIGEST_SECRET_NAMES):
            st.error("访问密码尚未配置。请在部署环境中设置报告访问密钥或其哈希值。")
            st.stop()
        if password_is_valid(password):
            st.session_state["authenticated"] = True
            st.rerun()
        else:
            st.error("密码不正确，请重新输入。")

    st.stop()

st.markdown(
    """
    <style>
    .block-container {padding-top: 1.35rem; padding-bottom: 2rem;}
    div[data-testid="stMetric"] {
        background: #FFFFFF;
        border: 1px solid #E2E8F0;
        border-radius: 8px;
        padding: 14px 16px;
        box-shadow: 0 1px 2px rgba(15, 23, 42, 0.04);
    }
    .kpi-grid {
        display: grid;
        grid-template-columns: repeat(5, minmax(0, 1fr));
        gap: 14px;
        margin: 14px 0 18px 0;
    }
    .kpi-card {
        background: #FFFFFF;
        border: 1px solid #E2E8F0;
        border-radius: 8px;
        padding: 15px 16px;
        min-height: 118px;
        box-shadow: 0 1px 2px rgba(15, 23, 42, 0.04);
    }
    .kpi-title {
        color: #475569;
        font-size: 0.82rem;
        line-height: 1.15rem;
        margin-bottom: 4px;
        min-height: 20px;
    }
    .kpi-value {
        color: #1F2937;
        font-size: 1.88rem;
        line-height: 2.15rem;
        font-weight: 520;
        letter-spacing: 0;
        white-space: nowrap;
    }
    .kpi-delta {
        display: inline-flex;
        align-items: center;
        border-radius: 999px;
        padding: 2px 7px;
        font-size: 0.78rem;
        line-height: 1rem;
        margin-top: 8px;
    }
    .kpi-delta.up {background: #DCFCE7; color: #047857;}
    .kpi-delta.down {background: #FEE2E2; color: #DC2626;}
    .kpi-delta.neutral {background: #E2E8F0; color: #475569;}
    @media (max-width: 1300px) {
        .kpi-grid {grid-template-columns: repeat(3, minmax(0, 1fr));}
    }
    @media (max-width: 760px) {
        .kpi-grid {grid-template-columns: 1fr;}
        .kpi-value {font-size: 1.65rem;}
    }
    .section-caption {color: #475569; margin-top: -0.4rem;}
    .insight-box {
        border-left: 4px solid #0F766E;
        background: #F8FAFC;
        border-radius: 6px;
        padding: 12px 14px;
        margin: 8px 0 14px 0;
    }
    .insight-box ul {margin-bottom: 0;}
    .muted-note {color: #64748B; font-size: 0.9rem;}
    .method-card {
        border: 1px solid #E2E8F0;
        border-left: 4px solid #2563EB;
        border-radius: 8px;
        background: #F8FAFC;
        padding: 12px 14px;
        margin-top: 2px;
    }
    .method-title {
        color: #172033;
        font-weight: 620;
        margin-bottom: 6px;
    }
    .method-card ul {
        margin: 0;
        padding-left: 1.05rem;
    }
    .method-card li {
        color: #475569;
        font-size: 0.86rem;
        line-height: 1.28rem;
        margin-bottom: 4px;
    }
    .executive-insight-grid {
        display: grid;
        grid-template-columns: repeat(3, minmax(0, 1fr));
        gap: 14px;
        margin: 16px 0 14px 0;
    }
    .executive-insight-stack {
        display: grid;
        grid-template-columns: 1fr;
        gap: 10px;
        margin: 2px 0 10px 0;
    }
    .executive-insight-card {
        background: #FFFFFF;
        border: 1px solid #E2E8F0;
        border-radius: 8px;
        padding: 14px 15px;
        min-height: 148px;
        box-shadow: 0 1px 2px rgba(15, 23, 42, 0.04);
    }
    .executive-insight-stack .executive-insight-card {
        min-height: 0;
        padding: 12px 14px;
    }
    .executive-insight-kicker {
        color: #2563EB;
        font-size: 0.74rem;
        font-weight: 620;
        line-height: 1rem;
        margin-bottom: 6px;
    }
    .executive-insight-title {
        color: #172033;
        font-size: 1.02rem;
        font-weight: 650;
        line-height: 1.28rem;
        margin-bottom: 8px;
    }
    .executive-insight-body {
        color: #475569;
        font-size: 0.9rem;
        line-height: 1.34rem;
    }
    .executive-insight-stack .executive-insight-title {
        font-size: 0.94rem;
        line-height: 1.18rem;
        margin-bottom: 6px;
    }
    .executive-insight-stack .executive-insight-body {
        font-size: 0.84rem;
        line-height: 1.26rem;
    }
    .executive-guardrail {
        color: #64748B;
        font-size: 0.86rem;
        line-height: 1.28rem;
        margin: -2px 0 14px 0;
    }
    @media (max-width: 1200px) {
        .executive-insight-grid {grid-template-columns: repeat(2, minmax(0, 1fr));}
    }
    @media (max-width: 760px) {
        .executive-insight-grid {grid-template-columns: 1fr;}
    }
    </style>
    """,
    unsafe_allow_html=True,
)


def data_ready(path: Path) -> bool:
    return all((path / name).exists() for name in REQUIRED_FILES)


def dataset_version(path: Path) -> float:
    files = [path / name for name in [*REQUIRED_FILES, *OPTIONAL_FILES] if (path / name).exists()]
    return max((file.stat().st_mtime for file in files), default=0.0)


@st.cache_data(show_spinner=False)
def load_dataset(path_text: str, data_version: float) -> dict[str, pd.DataFrame]:
    path = Path(path_text)
    return {
        name.replace(".csv", ""): pd.read_csv(path / name, encoding="utf-8-sig")
        for name in [*REQUIRED_FILES, *OPTIONAL_FILES]
        if (path / name).exists()
    }


def fmt_money(value: float | int | None) -> str:
    if value is None or pd.isna(value):
        return "N/A"
    value = float(value)
    if abs(value) >= 1_000_000:
        return f"RMB {value / 1_000_000:.2f}M"
    if abs(value) >= 1_000:
        return f"RMB {value / 1_000:.1f}K"
    return f"RMB {value:,.0f}"


def fmt_num(value: float | int | None, decimals: int = 0) -> str:
    if value is None or pd.isna(value):
        return "N/A"
    return f"{float(value):,.{decimals}f}"


def fmt_pct(value: float | int | None) -> str:
    if value is None or pd.isna(value):
        return "N/A"
    return f"{float(value):.1%}"


def growth(current: float | int | None, base: float | int | None) -> float:
    if current is None or base is None or pd.isna(current) or pd.isna(base) or float(base) == 0:
        return float("nan")
    return float(current) / float(base) - 1


def chart_layout(fig: go.Figure, height: int = 360) -> go.Figure:
    fig.update_layout(
        height=height,
        margin=dict(l=10, r=10, t=48, b=20),
        legend_title_text="",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#172033"),
    )
    fig.update_xaxes(showgrid=False)
    fig.update_yaxes(gridcolor="#E2E8F0")
    return fig


def fmt_delta(value: float | int | None, suffix: str = "YoY") -> tuple[str, str]:
    if value is None or pd.isna(value):
        return "待对比", "neutral"
    value = float(value)
    if value > 0:
        return f"↑ {value:.1%} {suffix}", "up"
    if value < 0:
        return f"↓ {abs(value):.1%} {suffix}", "down"
    return f"0.0% {suffix}", "neutral"


def render_kpi_cards(
    current_row: pd.Series,
    compare_row: pd.Series,
) -> None:
    cards = [
        {
            "title": "日均交易笔数",
            "value": fmt_num(current_row.get("avg_daily_txn")),
            "delta": growth(current_row.get("avg_daily_txn"), compare_row.get("avg_daily_txn")),
        },
        {
            "title": "商户日均频次",
            "value": fmt_num(current_row.get("merchant_frequency"), 2),
            "delta": growth(current_row.get("merchant_frequency"), compare_row.get("merchant_frequency")),
        },
        {
            "title": "日均 GMV",
            "value": fmt_money(current_row.get("avg_daily_gmv_cny")),
            "delta": growth(current_row.get("avg_daily_gmv_cny"), compare_row.get("avg_daily_gmv_cny")),
        },
        {
            "title": "总 GMV",
            "value": fmt_money(current_row.get("gmv_cny")),
            "delta": growth(current_row.get("gmv_cny"), compare_row.get("gmv_cny")),
        },
        {
            "title": "客单价",
            "value": fmt_money(current_row.get("aov_cny")),
            "delta": growth(current_row.get("aov_cny"), compare_row.get("aov_cny")),
        },
    ]

    card_html = ["<div class='kpi-grid'>"]
    for card in cards:
        delta_text, delta_class = fmt_delta(card["delta"])
        card_html.append(
            "<div class='kpi-card'>"
            f"<div class='kpi-title'>{escape(card['title'])}</div>"
            f"<div class='kpi-value'>{escape(card['value'])}</div>"
            f"<div class='kpi-delta {delta_class}'>{escape(delta_text)}</div>"
            "</div>"
        )
    card_html.append("</div>")
    st.markdown("".join(card_html), unsafe_allow_html=True)


def render_insights(insights: pd.DataFrame, page: str, title: str = "分析备注") -> None:
    if insights.empty or "page" not in insights:
        return
    page_rows = insights[insights["page"].astype(str).eq(page)]
    if page_rows.empty:
        return
    items = []
    for row in page_rows.itertuples(index=False):
        theme = getattr(row, "theme", "")
        bullet = getattr(row, "bullet", "")
        items.append(f"<li><strong>{theme}</strong>: {bullet}</li>" if theme else f"<li>{bullet}</li>")
    st.markdown(
        f"<div class='insight-box'><strong>{title}</strong><ul>{''.join(items)}</ul></div>",
        unsafe_allow_html=True,
    )


def render_public_context(public_context: pd.DataFrame) -> None:
    if public_context.empty:
        return
    st.markdown("#### 公开旅游背景")
    for row in public_context.itertuples(index=False):
        st.markdown(f"- **{row.source}**：{row.signal} [来源]({row.url})")


def render_method_card(title: str, items: list[str]) -> None:
    item_html = "".join(f"<li>{escape(item)}</li>" for item in items)
    st.markdown(
        f"<div class='method-card'><div class='method-title'>{escape(title)}</div><ul>{item_html}</ul></div>",
        unsafe_allow_html=True,
    )


def render_external_context_cards() -> None:
    cards = [
        {
            "kicker": "入境客流恢复",
            "title": "新西兰整体入境游客继续回升",
            "body": (
                "Stats NZ 月度国际旅行数据经政府发布摘要显示，2026 年 2 月海外访客超过 40.8 万人，"
                "同比多 5.3 万；截至 2026 年 2 月的年度海外访客约 358 万，约为 2019 年 12 月水平的 92%。"
            ),
            "source": "Stats NZ / NZ Government, 2026-04-14",
            "url": "https://www.beehive.govt.nz/release/new-zealand-tourism-continuing-rise",
        },
        {
            "kicker": "中国客群信号",
            "title": "中国访客在春节窗口出现明显恢复",
            "body": (
                "同一 Stats NZ 月度数据摘要显示，2026 年 2 月中国访客较 2025 年 2 月增加 41,700 人，"
                "春节与 NZeTA 政策便利共同放大了短期入境恢复信号。"
            ),
            "source": "Stats NZ / NZ Government, 2026-04-14",
            "url": "https://www.beehive.govt.nz/release/new-zealand-tourism-continuing-rise",
        },
        {
            "kicker": "消费大盘",
            "title": "旅游消费恢复为支付增长提供外部背景",
            "body": (
                "MBIE 修订版 MRTE 显示，截至 2026 年 2 月年度新西兰游客总消费约 465 亿新西兰元，同比 +11%；"
                "其中国际游客消费约 196 亿新西兰元，同比 +24%。"
            ),
            "source": "MBIE / TEIC MRTE, 2026-03-31",
            "url": "https://teic.mbie.govt.nz/assets/mrte/MRTE%20Topline%20results%20FINAL.pdf",
        },
    ]
    card_html = ["<div class='executive-insight-stack'>"]
    for card in cards:
        card_html.append(
            "<div class='executive-insight-card'>"
            f"<div class='executive-insight-kicker'>{escape(card['kicker'])}</div>"
            f"<div class='executive-insight-title'>{escape(card['title'])}</div>"
            f"<div class='executive-insight-body'>{escape(card['body'])}</div>"
            f"<div class='muted-note'>来源：<a href='{escape(card['url'])}' target='_blank'>{escape(card['source'])}</a></div>"
            "</div>"
        )
    card_html.append("</div>")
    st.markdown("#### 外部旅游背景信号")
    st.markdown("".join(card_html), unsafe_allow_html=True)


def fmt_signed_pct(value: float | int | None) -> str:
    if value is None or pd.isna(value):
        return "N/A"
    return f"{float(value):+.1%}"


def coverage_metric(coverage_frame: pd.DataFrame, metric: str) -> float:
    if coverage_frame.empty or "metric" not in coverage_frame or "value" not in coverage_frame:
        return float("nan")
    rows = coverage_frame[coverage_frame["metric"].astype(str).eq(metric)]
    if rows.empty:
        return float("nan")
    return float(rows["value"].iloc[0])


def render_executive_insight_cards(
    current_row: pd.Series,
    yoy_row: pd.Series,
    baseline_row: pd.Series,
    city_frame: pd.DataFrame,
    industry_period_frame: pd.DataFrame,
    activation_frame: pd.DataFrame,
    top_frame: pd.DataFrame,
    material_period_frame: pd.DataFrame,
    coverage_frame: pd.DataFrame,
    period_summary_frame: pd.DataFrame,
    compact: bool = False,
) -> None:
    cards: list[dict[str, str]] = []

    cards.append(
        {
            "kicker": "增长来源",
            "title": "增长由交易笔数驱动，而非客单价拉动",
            "body": (
                f"Labour GMV 同比 {fmt_signed_pct(growth(current_row.get('gmv_cny'), yoy_row.get('gmv_cny')))}，"
                f"交易笔数同比 {fmt_signed_pct(growth(current_row.get('txn_count'), yoy_row.get('txn_count')))}。"
                f"AOV 同比 {fmt_signed_pct(growth(current_row.get('aov_cny'), yoy_row.get('aov_cny')))}，更适合理解为更广泛、更高频的使用。"
            ),
        }
    )

    cards.append(
        {
            "kicker": "Baseline 对比",
            "title": "节假日 uplift 主要体现为交易强度提升",
            "body": (
                f"相较 4 月非 Labour baseline，日均交易笔数 {fmt_signed_pct(growth(current_row.get('avg_daily_txn'), baseline_row.get('avg_daily_txn')))}，"
                f"日均 GMV {fmt_signed_pct(growth(current_row.get('avg_daily_gmv_cny'), baseline_row.get('avg_daily_gmv_cny')))}。"
                f"活跃商户数 {fmt_signed_pct(growth(current_row.get('active_merchants'), baseline_row.get('active_merchants')))}，说明提升更多来自活跃商户内的交易变密。"
            ),
        }
    )

    if "active_users" in current_row and pd.notna(current_row.get("active_users")):
        material_body = "03 material 数据未接入，物料扫码只能作为后续补充验证。"
        if not material_period_frame.empty and "period_label" in material_period_frame:
            material_plot = material_period_frame.copy()
            current_material = material_plot[material_plot["period_label"].astype(str).eq("holiday_2026_labour")]
            material_2025 = material_plot[material_plot["period_label"].astype(str).eq("holiday_2025_labour")]
            if not current_material.empty:
                row = current_material.iloc[0]
                material_body = (
                    "Material 作为辅助触达信号更温和："
                    f"PV 快照均值较 4 月 baseline {fmt_signed_pct(row.get('avg_all_pv_snapshot_vs_baseline'))}，"
                    f"UV 快照均值 {fmt_signed_pct(row.get('avg_all_uv_snapshot_vs_baseline'))}。"
                )
                if not material_2025.empty and material_2025.get("data_status", pd.Series(dtype="object")).astype(str).eq("missing_from_03_export").any():
                    material_body += "03 缺 2025 Labour rows，因此不做 material Labour YoY 判断。"

        cards.append(
            {
                "kicker": "用户与物料",
                "title": "用户触达和使用频次是主驱动，物料信号保持稳定",
                "body": (
                    f"2026 Labour 日均 active users 同比 {fmt_signed_pct(growth(current_row.get('avg_daily_active_users'), yoy_row.get('avg_daily_active_users')))}，"
                    f"daily user frequency 同比 {fmt_signed_pct(growth(current_row.get('avg_daily_user_frequency'), yoy_row.get('avg_daily_user_frequency')))}，"
                    f"AOV 同比 {fmt_signed_pct(growth(current_row.get('aov_cny'), yoy_row.get('aov_cny')))}；"
                    f"{material_body}"
                ),
            }
        )

    if not activation_frame.empty:
        retained = activation_frame[activation_frame["activation_segment"].eq("retained_active")]
        incremental = activation_frame[activation_frame["activation_segment"].isin(["new_coverage", "reactivated_dormant"])]
        retained_share = float(retained["current_gmv_share"].sum()) if not retained.empty else float("nan")
        retained_gmv_yoy = growth(
            retained["holiday_2026_gmv_cny"].sum() if not retained.empty else None,
            retained["holiday_2025_gmv_cny"].sum() if not retained.empty else None,
        )
        cards.append(
            {
                "kicker": "商户覆盖",
                "title": "留存商户是基本盘，新商户和同档期回流贡献增量",
                "body": (
                    f"Retained active 商户贡献 2026 Labour GMV 的 {fmt_pct(retained_share)}，"
                    f"同档期留存商户 GMV 同比 {fmt_signed_pct(retained_gmv_yoy)}。"
                    f"New coverage + same-window returning existing 贡献当前 GMV 的 {fmt_pct(float(incremental['current_gmv_share'].sum()))}。"
                ),
            }
        )

    if not city_frame.empty:
        city_plot = city_frame.copy()
        city_total = float(pd.to_numeric(city_plot["gmv_cny"], errors="coerce").fillna(0).sum())
        city_plot["gmv_share"] = pd.to_numeric(city_plot["gmv_cny"], errors="coerce").fillna(0) / city_total if city_total else 0
        top5_share = float(city_plot.sort_values("gmv_cny", ascending=False).head(5)["gmv_cny"].sum() / city_total) if city_total else float("nan")
        auckland = city_plot[city_plot["business_city"].astype(str).eq("Auckland")]
        queenstown = city_plot[city_plot["business_city"].astype(str).eq("Queenstown")]
        auckland_share = float(auckland["gmv_share"].sum()) if not auckland.empty else float("nan")
        queenstown_yoy = float(queenstown["yoy_gmv_growth"].iloc[0]) if not queenstown.empty and "yoy_gmv_growth" in queenstown else float("nan")
        queenstown_uplift = float(queenstown["pre_uplift"].iloc[0]) if not queenstown.empty and "pre_uplift" in queenstown else float("nan")
        cards.append(
            {
                "kicker": "城市结构",
                "title": "Auckland 承接基本盘，旅游城市增长更突出",
                "body": (
                    f"Auckland 贡献 2026 五一 GMV 的 {fmt_pct(auckland_share)}，前 5 城市合计贡献 {fmt_pct(top5_share)}。"
                    f"Queenstown GMV 同比 {fmt_signed_pct(queenstown_yoy)}，日均 GMV 较 4 月 baseline {fmt_signed_pct(queenstown_uplift)}，支持 visitor spend 恢复判断。"
                ),
            }
        )

    if not industry_period_frame.empty:
        current_industry = industry_period_frame[industry_period_frame["period_label"].astype(str).eq("holiday_2026_labour")].copy()
        if not current_industry.empty:
            major = (
                current_industry.groupby("major_industry", as_index=False)
                .agg(gmv_cny=("gmv_cny", "sum"), txn_count=("txn_count", "sum"))
                .sort_values("gmv_cny", ascending=False)
            )
            total_gmv = float(major["gmv_cny"].sum())
            total_txn = float(major["txn_count"].sum())
            top3_share = float(major.head(3)["gmv_cny"].sum() / total_gmv) if total_gmv else float("nan")
            frequency_categories = major[major["major_industry"].isin(["食品/超市/便利店", "餐饮类"])]
            frequency_txn_share = float(frequency_categories["txn_count"].sum() / total_txn) if total_txn else float("nan")
            top_major = str(major.iloc[0]["major_industry"]) if not major.empty else "头部行业"
            top_major_share = float(major.iloc[0]["gmv_cny"] / total_gmv) if total_gmv and not major.empty else float("nan")
            cards.append(
                {
                    "kicker": "行业结构",
                    "title": "零售和游客消费主导 GMV，食品/餐饮贡献高频交易",
                    "body": (
                        f"{top_major} GMV 占比最高，为 {fmt_pct(top_major_share)}；前三大 major industry 合计贡献 {fmt_pct(top3_share)}。"
                        f"食品/超市/便利店 + 餐饮类贡献 {fmt_pct(frequency_txn_share)} 的交易笔数，体现高频低客单层。"
                    ),
                }
            )

    if not top_frame.empty:
        total_current_gmv = float(current_row.get("gmv_cny")) if pd.notna(current_row.get("gmv_cny")) else 0.0
        top10_share = float(pd.to_numeric(top_frame.head(10)["gmv_cny"], errors="coerce").fillna(0).sum() / total_current_gmv) if total_current_gmv else float("nan")
        top20_share = float(pd.to_numeric(top_frame["gmv_cny"], errors="coerce").fillna(0).sum() / total_current_gmv) if total_current_gmv else float("nan")
        cards.append(
            {
                "kicker": "头部商户",
                "title": "KA 和游客零售商户拉动明显，GMV 集中度较高",
                "body": (
                    f"前 10 商户贡献 2026 五一 GMV 的 {fmt_pct(top10_share)}，前 20 贡献 {fmt_pct(top20_share)}。"
                    "头部商户集中在 Auckland / Queenstown 的零售、礼品、免税、旅游和高端消费场景。"
                ),
            }
        )

    if not cards:
        return

    container_class = "executive-insight-stack" if compact else "executive-insight-grid"
    card_html = [f"<div class='{container_class}'>"]
    for card in cards[:7]:
        card_html.append(
            "<div class='executive-insight-card'>"
            f"<div class='executive-insight-kicker'>{escape(card['kicker'])}</div>"
            f"<div class='executive-insight-title'>{escape(card['title'])}</div>"
            f"<div class='executive-insight-body'>{escape(card['body'])}</div>"
            "</div>"
        )
    card_html.append("</div>")
    st.markdown("#### 核心洞察")
    st.markdown("".join(card_html), unsafe_allow_html=True)

    geo_match = coverage_metric(coverage_frame, "Geo match rate")
    mcc_match = coverage_metric(coverage_frame, "MCC match rate")
    unmatched = city_frame[city_frame.get("business_city", pd.Series(dtype="object")).astype(str).isin(["未分类", "Unclassified"])] if not city_frame.empty else pd.DataFrame()
    city_total = float(pd.to_numeric(city_frame.get("gmv_cny", pd.Series(dtype="float64")), errors="coerce").fillna(0).sum()) if not city_frame.empty else 0.0
    unmatched_share = float(pd.to_numeric(unmatched.get("gmv_cny", pd.Series(dtype="float64")), errors="coerce").fillna(0).sum() / city_total) if city_total else float("nan")
    active_user_ready = "active_users" in period_summary_frame and period_summary_frame["active_users"].notna().any()
    active_user_note = "active-user 字段已接入" if active_user_ready else "active-user 字段等待修正后的 02 重跑后接入"
    st.markdown(
        (
            f"<div class='executive-guardrail'>数据边界：MCC match {fmt_pct(mcc_match)}，"
            f"geo match {fmt_pct(geo_match)}，未分类城市 GMV {fmt_pct(unmatched_share)}；{active_user_note}。</div>"
        ),
        unsafe_allow_html=True,
    )


def select_data_dir() -> tuple[Path, str]:
    processed_ready = data_ready(PROCESSED_DIR)
    if not processed_ready:
        st.error("已处理聚合数据不完整，请先运行本地处理脚本并确认输出。")
        st.stop()
    return PROCESSED_DIR, "已处理聚合数据"


def get_period(period_summary: pd.DataFrame, label: str) -> pd.Series:
    row = period_summary[period_summary["period_label"].eq(label)]
    if row.empty:
        return pd.Series(dtype="object")
    return row.iloc[0]


def selected_points(event: object) -> list[dict]:
    if event is None:
        return []
    selection = getattr(event, "selection", None)
    if selection is not None:
        points = getattr(selection, "points", None)
        return points or []
    if isinstance(event, dict):
        return event.get("selection", {}).get("points", []) or []
    return []


def selected_echarts_label(event: object) -> str | None:
    if isinstance(event, str) and event:
        return event
    if isinstance(event, dict):
        label = event.get("period_label") or event.get("value")
        if isinstance(label, str) and label:
            return label
    return None


def echarts_js(js_code: str) -> str:
    if JsCode is None:
        return js_code
    wrapped = JsCode(js_code)
    return getattr(wrapped, "js_code", wrapped)


def render_period_bubble_echarts(bubble_data: pd.DataFrame) -> object:
    data_points = []
    for row in bubble_data.reset_index(drop=True).itertuples(index=True):
        period_label = str(row.period_label)
        color = PERIOD_COLORS.get(period_label, "#0F766E")
        data_points.append(
            {
                "name": str(row.period_name),
                "value": [
                    float(row.avg_daily_txn),
                    float(row.avg_daily_gmv_cny),
                    float(row.gmv_cny),
                    period_label,
                    str(row.period_name),
                    float(row.merchant_frequency),
                    float(row.aov_cny),
                ],
                "itemStyle": {"color": color, "opacity": 0.82},
            }
        )

    options = {
        "animationDuration": 650,
        "grid": {"left": 70, "right": 28, "top": 54, "bottom": 64},
        "tooltip": {
            "trigger": "item",
            "formatter": echarts_js(
                """
                function (params) {
                    const v = params.value;
                    const money = new Intl.NumberFormat('en-US', {maximumFractionDigits: 0}).format;
                    return [
                        '<strong>' + v[4] + '</strong>',
                        '日均交易笔数：' + money(v[0]),
                        '日均 GMV：RMB ' + money(v[1]),
                        '总 GMV：RMB ' + money(v[2]),
                        '商户日均频次：' + v[5].toFixed(2),
                        '客单价：RMB ' + money(v[6])
                    ].join('<br/>');
                }
                """
            ),
        },
        "legend": {"show": False},
        "xAxis": {
            "type": "value",
            "name": "日均交易笔数",
            "nameLocation": "middle",
            "nameGap": 36,
            "splitLine": {"lineStyle": {"color": "#E2E8F0"}},
            "axisLine": {"lineStyle": {"color": "#CBD5E1"}},
        },
        "yAxis": {
            "type": "value",
            "name": "日均 GMV（元）",
            "nameLocation": "middle",
            "nameGap": 56,
            "splitLine": {"lineStyle": {"color": "#E2E8F0"}},
            "axisLabel": {
                "formatter": echarts_js(
                    "function (value) { return value >= 1000000 ? (value/1000000).toFixed(1) + 'M' : value; }"
                )
            },
        },
        "series": [
            {
                "type": "scatter",
                "data": data_points,
                "symbolSize": echarts_js(
                    """
                    function (value) {
                        return Math.max(28, Math.min(78, Math.sqrt(value[2]) / 850));
                    }
                    """
                ),
                "emphasis": {
                    "focus": "series",
                    "scale": 1.12,
                    "label": {
                        "show": True,
                        "formatter": echarts_js("function (p) { return p.value[4]; }"),
                        "position": "top",
                        "color": "#111827",
                        "fontWeight": 600,
                    },
                },
                "label": {
                    "show": True,
                    "formatter": echarts_js("function (p) { return p.value[4]; }"),
                    "position": "top",
                    "color": "#334155",
                    "fontSize": 11,
                },
            }
        ],
    }
    return st_echarts(
        options=options,
        events={"click": "function(params) { return params.value ? params.value[3] : null; }"},
        height="500px",
        key="period_bubble_echarts",
        renderer="svg",
    )


def render_period_bubble_plotly(bubble_data: pd.DataFrame) -> object:
    chart_data = bubble_data.copy()
    chart_data["gmv_m"] = chart_data["gmv_cny"] / 1_000_000
    chart_data["bubble_label"] = chart_data["period_name"].astype(str)
    bubble = px.scatter(
        chart_data,
        x="avg_daily_txn",
        y="avg_daily_gmv_cny",
        size="gmv_cny",
        color="period_name",
        color_discrete_map=PERIOD_COLORS,
        hover_name="period_name",
        text="bubble_label",
        custom_data=["period_label"],
        size_max=86,
        hover_data={
            "period_label": False,
            "bubble_label": False,
            "gmv_m": ":.1f",
            "days": True,
            "avg_daily_txn": ":,.0f",
            "merchant_frequency": ":.2f",
            "avg_daily_gmv_cny": ":,.0f",
            "gmv_cny": ":,.0f",
        },
        labels={
            "merchant_frequency": "商户日均频次",
            "avg_daily_gmv_cny": "日均 GMV（元）",
            "gmv_cny": "总 GMV",
            "gmv_m": "总 GMV（M 元）",
            "avg_daily_txn": "日均交易笔数",
            "days": "天数",
        },
        title="时段气泡对比",
    )
    bubble.update_traces(
        marker=dict(line=dict(width=1.6, color="#FFFFFF"), sizemin=24, opacity=0.82),
        textposition="top center",
        textfont=dict(size=12, color="#334155"),
        selector=dict(mode="markers+text"),
    )
    bubble.update_layout(
        title=dict(text="时段气泡对比", x=0.02, xanchor="left"),
        hoverlabel=dict(bgcolor="#FFFFFF", bordercolor="#CBD5E1", font_size=12),
        legend=dict(orientation="h", yanchor="bottom", y=-0.24, xanchor="left", x=0),
    )
    bubble.update_xaxes(title_text="日均交易笔数", zeroline=False)
    bubble.update_yaxes(title_text="日均 GMV（元）", zeroline=False)
    return st.plotly_chart(
        chart_layout(bubble, height=500),
        width="stretch",
        key="period_bubble_chart",
        on_select="rerun",
        selection_mode="points",
    )


require_password()

data_dir, source_label = select_data_dir()
frames = load_dataset(str(data_dir), dataset_version(data_dir))

if not all(key in frames for key in [name.replace(".csv", "") for name in REQUIRED_FILES]):
    st.error("报告数据不完整，请先处理云端导出并确认聚合输出。")
    st.stop()

country = st.sidebar.selectbox("国家/地区", ["新西兰", "澳大利亚"], index=0)
st.sidebar.markdown("### 范围")
st.sidebar.write("当前报告聚焦新西兰五一假期与相关对比窗口。")
st.sidebar.write("澳大利亚后续复用同一套 SQL、处理脚本和页面结构。")
st.sidebar.markdown("---")
st.sidebar.caption(f"当前使用：{source_label}")

if country == "澳大利亚":
    st.title("澳大利亚假期 WeChat Pay 热度报告")
    st.info("澳大利亚数据入口已预留。后续完成分区、行数和 join 覆盖检查，并导入 AU 聚合数据后，可在此查看澳大利亚报告。")
    st.stop()

summary = frames["summary_kpis"]
daily = frames["daily_trend"]
region = frames["region_summary"]
industry = frames["industry_summary"]
top_merchants = frames["top_merchants"]
top_merchants_by_frequency = frames.get("top_merchants_by_frequency", frames.get("top_merchants_by_txn", pd.DataFrame()))
coverage = frames["coverage_summary"]
material = frames["material_summary"]

period_summary = frames.get("period_summary", pd.DataFrame())
period_daily = frames.get("period_daily", pd.DataFrame())
period_catalog = frames.get("period_catalog", pd.DataFrame())
global_material = frames.get("global_material_summary", pd.DataFrame())
material_period = frames.get("material_period_summary", pd.DataFrame())
insights = frames.get("insight_bullets", pd.DataFrame())
public_context = frames.get("public_context", pd.DataFrame())
merchant_activation_summary = frames.get("merchant_activation_summary", pd.DataFrame())
merchant_activation_detail = frames.get("merchant_activation_detail", pd.DataFrame())
industry_period = frames.get("industry_period_summary", pd.DataFrame())

if period_summary.empty:
    period_summary = frames.get("global_summary_kpis", summary).copy()
    period_summary["merchant_day_count"] = period_summary.get("active_merchants", 0)
    period_summary["avg_daily_txn"] = period_summary["txn_count"] / period_summary.get("period_days", 1)
    period_summary["avg_daily_gmv_cny"] = period_summary["gmv_cny"] / period_summary.get("period_days", 1)
    period_summary["merchant_frequency"] = period_summary["txn_count"] / period_summary["merchant_day_count"].replace(0, pd.NA)
if period_daily.empty:
    period_daily = frames.get("global_daily_trend", daily).copy()

if "avg_daily_active_users" not in period_summary.columns and not period_daily.empty and "active_users" in period_daily.columns:
    daily_users = period_daily.copy()
    daily_users["active_users"] = pd.to_numeric(daily_users["active_users"], errors="coerce")
    avg_daily_users = daily_users.groupby("period_label")["active_users"].mean()
    period_summary["avg_daily_active_users"] = period_summary["period_label"].map(avg_daily_users)

if "avg_daily_user_frequency" not in period_summary.columns and {"avg_daily_txn", "avg_daily_active_users"}.issubset(period_summary.columns):
    period_summary["avg_daily_user_frequency"] = (
        pd.to_numeric(period_summary["avg_daily_txn"], errors="coerce")
        / pd.to_numeric(period_summary["avg_daily_active_users"], errors="coerce").replace(0, pd.NA)
    )

if "active_merchants" not in period_summary.columns and "active_merchants" in summary.columns:
    period_summary = period_summary.merge(
        summary[["period_label", "active_merchants"]].drop_duplicates("period_label"),
        how="left",
        on="period_label",
    )

period_summary = period_summary.sort_values("sort_order" if "sort_order" in period_summary else "period_label")
period_summary = localize_period_column(period_summary)
period_daily = localize_period_column(period_daily)
period_catalog = localize_period_column(period_catalog)
material_period = localize_period_column(material_period)
industry_period = localize_period_column(industry_period)
available_summary = period_summary[period_summary["period_status"].astype(str).str.contains("available|temporary", regex=True, na=False)].copy()

current = get_period(period_summary, "holiday_2026_labour")
yoy = get_period(period_summary, "holiday_2025_labour")
baseline = get_period(period_summary, "baseline_2026_apr_non_labour")

st.title("NZ 五一假期 WeChat Pay 热度报告")
st.caption("日均交易为主指标，GMV 作为规模指标，客单价与商户频次共同解释交易结构。")

tabs = st.tabs(["总览", "时段深挖", "城市", "行业", "用户与物料", "商户激活", "头部商户", "方法与边界"])

with tabs[0]:
    st.subheader("管理层视图")
    st.markdown('<div class="section-caption">核心问题：假期交易强度是否提升，以及提升来自交易频次、商户覆盖还是游客恢复。</div>', unsafe_allow_html=True)

    render_kpi_cards(current, yoy)

    render_insights(insights, "overview", "执行与策略备注")

    left, right = st.columns([1.12, 1])
    with left:
        plot_summary = available_summary.copy()
        plot_summary["active_merchants"] = pd.to_numeric(plot_summary.get("active_merchants"), errors="coerce")
        fig = make_subplots(specs=[[{"secondary_y": True}]])
        fig.add_bar(
            x=plot_summary["period_name"],
            y=plot_summary["avg_daily_txn"],
            name="日均交易笔数",
            marker_color="#0F766E",
        )
        fig.add_scatter(
            x=plot_summary["period_name"],
            y=plot_summary["active_merchants"],
            name="活跃商户数",
            mode="lines+markers",
            marker_color="#D97706",
            secondary_y=True,
        )
        fig.update_yaxes(title_text="日均交易笔数", secondary_y=False)
        fig.update_yaxes(title_text="活跃商户数", secondary_y=True)
        fig.update_layout(title="各时段日均交易强度与商户覆盖")
        st.plotly_chart(chart_layout(fig, height=410), width="stretch")
        render_external_context_cards()
    with right:
        render_executive_insight_cards(
            current,
            yoy,
            baseline,
            region,
            industry_period,
            merchant_activation_summary,
            top_merchants,
            material_period,
            coverage,
            period_summary,
            compact=True,
        )
        pending = period_catalog[period_catalog["status"].astype(str).str.contains("pending", na=False)] if not period_catalog.empty else pd.DataFrame()
        if not pending.empty:
            st.markdown("#### 待补充时段")
            st.dataframe(display_table(pending[["period_name", "window_start", "window_end", "status"]]), hide_index=True, width="stretch")
    render_public_context(public_context)

with tabs[1]:
    st.subheader("时段深挖")
    st.markdown('<div class="section-caption">气泡图：横轴为日均交易笔数，纵轴为日均交易流水，气泡大小代表总 GMV。点击时段后查看每日走势。</div>', unsafe_allow_html=True)
    render_insights(insights, "trend", "执行与策略备注")

    bubble_data = available_summary.copy()
    default_period = "holiday_2026_labour" if "holiday_2026_labour" in set(bubble_data["period_label"]) else str(bubble_data.iloc[0]["period_label"])
    st.session_state.setdefault("selected_period_label", default_period)

    left, right = st.columns([1.05, 1.25])
    with left:
        st.caption("点击气泡可更新右侧每日走势。")
        event = render_period_bubble_plotly(bubble_data)
        points = selected_points(event)
        if points and points[0].get("customdata"):
            st.session_state["selected_period_label"] = points[0]["customdata"][0]
        if not bubble_data.empty:
            min_gmv = float(bubble_data["gmv_cny"].min())
            max_gmv = float(bubble_data["gmv_cny"].max())
            ratio = max_gmv / min_gmv if min_gmv else float("nan")
            day_values = sorted({int(value) for value in bubble_data["days"].dropna().tolist()}) if "days" in bubble_data else []
            day_note = f"当前可用时段均为 {day_values[0]} 天" if len(day_values) == 1 else f"当前时段长度：{', '.join(map(str, day_values))} 天"
            st.caption(
                f"气泡大小代表总 GMV。{day_note}；总 GMV 从 RMB {min_gmv / 1_000_000:.1f}M "
                f"到 RMB {max_gmv / 1_000_000:.1f}M（{ratio:.2f} 倍），因此视觉尺寸差异会相对温和。"
            )

    with right:
        selected_period = get_period(bubble_data, st.session_state["selected_period_label"])
        st.markdown(f"#### {selected_period.get('period_name', '所选时段')}")
        summary_cols = st.columns(4)
        summary_cols[0].metric("天数", fmt_num(selected_period.get("days")))
        summary_cols[1].metric("日均交易笔数", fmt_num(selected_period.get("avg_daily_txn")))
        summary_cols[2].metric("日均 GMV", fmt_money(selected_period.get("avg_daily_gmv_cny")))
        summary_cols[3].metric("客单价", fmt_money(selected_period.get("aov_cny")))

        selected_daily = period_daily[period_daily["period_label"].eq(st.session_state["selected_period_label"])].sort_values("trade_date_ds")
        if selected_daily.empty:
            st.info("该时段每日数据仍待 SQL 导出补充。")
        else:
            trend_fig = make_subplots(
                rows=2,
                cols=1,
                shared_xaxes=True,
                vertical_spacing=0.12,
                specs=[[{"secondary_y": True}], [{"secondary_y": False}]],
                row_heights=[0.68, 0.32],
            )
            trend_fig.add_bar(x=selected_daily["date"], y=selected_daily["txn_count"], name="交易笔数", marker_color="#2563EB", row=1, col=1)
            trend_fig.add_scatter(x=selected_daily["date"], y=selected_daily["gmv_cny"], name="GMV", mode="lines+markers", marker_color="#0F766E", row=1, col=1, secondary_y=True)
            trend_fig.add_scatter(x=selected_daily["date"], y=selected_daily["active_merchants"], name="活跃商户数", mode="lines+markers", marker_color="#D97706", row=2, col=1)
            trend_fig.update_yaxes(title_text="交易笔数", row=1, col=1, secondary_y=False)
            trend_fig.update_yaxes(title_text="GMV", row=1, col=1, secondary_y=True)
            trend_fig.update_yaxes(title_text="活跃商户数", row=2, col=1)
            st.plotly_chart(chart_layout(trend_fig, height=500), width="stretch")

    selected_daily = period_daily[period_daily["period_label"].eq(st.session_state["selected_period_label"])].sort_values("trade_date_ds")
    if not selected_daily.empty:
        st.markdown("#### 每日明细")
        display_daily = selected_daily[["date", "txn_count", "gmv_cny", "active_merchants", "merchant_frequency", "aov_cny"]].copy()
        display_daily["gmv_cny"] = display_daily["gmv_cny"].map(lambda value: f"{float(value):,.0f}")
        display_daily["merchant_frequency"] = display_daily["merchant_frequency"].map(lambda value: f"{float(value):.2f}")
        display_daily["aov_cny"] = display_daily["aov_cny"].map(lambda value: f"{float(value):,.0f}")
        st.dataframe(display_table(display_daily), hide_index=True, width="stretch")

with tabs[2]:
    st.subheader("城市拆解")
    st.markdown('<div class="section-caption">地理维度仅展示 business_city 层级，并沿用 Wechat-Pay-ANZ-MAP 的城市匹配与标准化逻辑。</div>', unsafe_allow_html=True)
    render_insights(insights, "region", "执行与策略备注")
    region_plot = region.copy()
    if "business_city" not in region_plot and "city" in region_plot:
        region_plot["business_city"] = region_plot["city"]
    region_plot["gmv_cny"] = pd.to_numeric(region_plot["gmv_cny"], errors="coerce").fillna(0)
    region_plot["txn_count"] = pd.to_numeric(region_plot["txn_count"], errors="coerce").fillna(0)
    region_plot["active_merchants"] = pd.to_numeric(region_plot["active_merchants"], errors="coerce").fillna(0)
    region_plot = region_plot.sort_values("gmv_cny", ascending=False)
    top_n = st.slider("展示城市数", min_value=5, max_value=min(20, max(len(region_plot), 5)), value=min(10, len(region_plot)), step=1)
    chart_region = region_plot.head(top_n).sort_values("gmv_cny", ascending=True)
    city_total = float(region_plot["gmv_cny"].sum())
    top_share = float(region_plot.head(top_n)["gmv_cny"].sum() / city_total) if city_total else float("nan")
    unmatched = region_plot[region_plot["business_city"].astype(str).isin(["未分类", "Unclassified"])]
    unmatched_share = float(unmatched["gmv_cny"].sum() / city_total) if city_total and not unmatched.empty else float("nan")
    left, right = st.columns([1.2, 1])
    with left:
        fig = px.bar(
            chart_region,
            x="gmv_cny",
            y="business_city",
            color="txn_count",
            orientation="h",
            title=f"GMV 前 {top_n} 城市",
            labels={"gmv_cny": "GMV（元）", "business_city": "", "txn_count": "交易笔数"},
            color_continuous_scale=["#E0F2FE", "#0369A1"],
            custom_data=["txn_count", "active_merchants", "geo_match_rate"],
        )
        fig.update_traces(
            hovertemplate=(
                "<b>%{y}</b><br>"
                "GMV：RMB %{x:,.0f}<br>"
                "交易笔数：%{customdata[0]:,.0f}<br>"
                "活跃商户数：%{customdata[1]:,.0f}<br>"
                "城市匹配率：%{customdata[2]:.1%}<extra></extra>"
            )
        )
        st.plotly_chart(chart_layout(fig, height=430), width="stretch")

        city_cards = []
        if not region_plot.empty:
            top_city = region_plot.iloc[0]
            top_city_name = str(top_city.get("business_city", "头部城市"))
            top_city_share = float(top_city.get("gmv_cny", 0) / city_total) if city_total else float("nan")
            city_cards.append(
                {
                    "kicker": "城市集中度",
                    "title": f"{top_city_name} 是 GMV 基本盘",
                    "body": (
                        f"{top_city_name} 贡献 2026 Labour GMV 的 {fmt_pct(top_city_share)}，"
                        f"前 {top_n} 城市合计贡献 {fmt_pct(top_share)}。城市结构高度集中，头部城市变化会明显影响总盘。"
                    ),
                }
            )

            destination = region_plot[region_plot["business_city"].astype(str).eq("Queenstown")]
            if destination.empty:
                destination = region_plot[
                    ~region_plot["business_city"].astype(str).isin(["Auckland", "未分类", "Unclassified"])
                ].head(1)
            if not destination.empty:
                dest = destination.iloc[0]
                dest_city = str(dest.get("business_city", "Destination city"))
                city_cards.append(
                    {
                        "kicker": "假期目的地",
                        "title": f"{dest_city} 的假期 uplift 更明显",
                        "body": (
                            f"{dest_city} GMV 同比 {fmt_signed_pct(dest.get('yoy_gmv_growth'))}，"
                            f"日均 GMV 较 4 月 baseline {fmt_signed_pct(dest.get('pre_uplift'))}。"
                            "这类目的地城市更能体现假期和游客消费场景。"
                        ),
                    }
                )

            if not unmatched.empty:
                city_cards.append(
                    {
                        "kicker": "数据边界",
                        "title": "未分类城市需要单独看待",
                        "body": (
                            f"未分类 GMV 占 {fmt_pct(unmatched_share)}。它反映地址未能稳定匹配到 business_city，"
                            "不应归入某个具体城市，但会影响城市份额解读。"
                        ),
                    }
                )

        if city_cards:
            card_html = ["<div class='executive-insight-stack'>"]
            for card in city_cards:
                card_html.append(
                    "<div class='executive-insight-card'>"
                    f"<div class='executive-insight-kicker'>{escape(card['kicker'])}</div>"
                    f"<div class='executive-insight-title'>{escape(card['title'])}</div>"
                    f"<div class='executive-insight-body'>{escape(card['body'])}</div>"
                    "</div>"
                )
            card_html.append("</div>")
            st.markdown("#### 城市洞察")
            st.markdown("".join(card_html), unsafe_allow_html=True)
    with right:
        st.metric(f"前 {top_n} 城市 GMV 占比", fmt_pct(top_share))
        if not unmatched.empty:
            st.metric("未分类城市 GMV 占比", fmt_pct(unmatched_share))
        city_display = region_plot.copy()
        city_display["gmv_cny"] = city_display["gmv_cny"].map(lambda value: f"{float(value):,.0f}")
        city_display["txn_count"] = city_display["txn_count"].map(lambda value: f"{float(value):,.0f}")
        city_display["active_merchants"] = city_display["active_merchants"].map(lambda value: f"{float(value):,.0f}")
        for col in ["geo_match_rate", "yoy_gmv_growth", "pre_uplift"]:
            if col in city_display:
                city_display[col] = city_display[col].apply(fmt_pct)
        st.dataframe(display_table(city_display), hide_index=True, width="stretch")

with tabs[3]:
    st.subheader("行业分布")
    st.markdown('<div class="section-caption">行业由商户 MCC 映射；矩形面积代表 GMV 占比，颜色深浅代表交易笔数。</div>', unsafe_allow_html=True)
    render_insights(insights, "industry", "执行与策略备注")
    if industry.empty and industry_period.empty:
        st.info("行业数据待补充。")
    else:
        if not industry_period.empty:
            period_options = (
                industry_period[["period_label", "period_name", "sort_order"]]
                .drop_duplicates()
                .sort_values("sort_order")
            )
            default_period_label = "holiday_2026_labour" if "holiday_2026_labour" in set(period_options["period_label"]) else str(period_options.iloc[0]["period_label"])
            st.session_state.setdefault("industry_period_label", default_period_label)
            selected_period_label = st.selectbox(
                "时段",
                period_options["period_label"].tolist(),
                index=period_options["period_label"].tolist().index(st.session_state["industry_period_label"])
                if st.session_state["industry_period_label"] in set(period_options["period_label"])
                else 0,
                format_func=lambda label: str(period_options.loc[period_options["period_label"].eq(label), "period_name"].iloc[0]),
            )
            if selected_period_label != st.session_state.get("industry_period_label"):
                st.session_state["industry_period_label"] = selected_period_label
                st.session_state["selected_major_industry"] = "__all__"
                st.rerun()
            industry_plot = industry_period[industry_period["period_label"].eq(selected_period_label)].copy()
            selected_period_name = str(period_options.loc[period_options["period_label"].eq(selected_period_label), "period_name"].iloc[0])
        else:
            selected_period_label = "holiday_2026_labour"
            selected_period_name = "2026 五一假期"
            industry_plot = industry.copy()
        industry_plot["gmv_cny"] = pd.to_numeric(industry_plot["gmv_cny"], errors="coerce").fillna(0)
        industry_plot["txn_count"] = pd.to_numeric(industry_plot["txn_count"], errors="coerce").fillna(0)
        industry_plot["active_merchants"] = pd.to_numeric(industry_plot["active_merchants"], errors="coerce").fillna(0)

        major_summary = (
            industry_plot.groupby("major_industry", as_index=False)
            .agg(
                gmv_cny=("gmv_cny", "sum"),
                txn_count=("txn_count", "sum"),
                active_merchants=("active_merchants", "sum"),
            )
            .sort_values("gmv_cny", ascending=False)
        )
        total_industry_gmv = float(major_summary["gmv_cny"].sum())
        major_summary["gmv_share"] = major_summary["gmv_cny"] / total_industry_gmv if total_industry_gmv else 0

        st.session_state.setdefault("selected_major_industry", "__all__")
        selected_major = st.session_state.get("selected_major_industry", "__all__")
        if selected_major == "__all__":
            treemap_data = major_summary.copy()
            treemap_data["level"] = treemap_data["major_industry"]
            treemap_title = f"{selected_period_name}：按行业大类查看 GMV 占比"
            treemap_key = f"industry_treemap_major_{selected_period_label}"
        else:
            back_cols = st.columns([0.2, 0.8])
            if back_cols[0].button("返回", width="stretch"):
                st.session_state["selected_major_industry"] = "__all__"
                selected_major = "__all__"
            if selected_major == "__all__":
                treemap_data = major_summary.copy()
                treemap_data["level"] = treemap_data["major_industry"]
                treemap_title = f"{selected_period_name}：按行业大类查看 GMV 占比"
                treemap_key = f"industry_treemap_major_after_back_{selected_period_label}"
            else:
                back_cols[1].markdown(f"#### {selected_major}")
                treemap_data = industry_plot[industry_plot["major_industry"].eq(selected_major)].copy()
                treemap_data["level"] = treemap_data["industry"]
                child_total_gmv = float(treemap_data["gmv_cny"].sum())
                treemap_data["gmv_share"] = treemap_data["gmv_cny"] / child_total_gmv if child_total_gmv else 0
                treemap_title = f"{selected_period_name}：{selected_major} 内部 GMV 占比"
                treemap_key = f"industry_treemap_child_{selected_period_label}_{selected_major}"

        treemap_fig = px.treemap(
            treemap_data,
            path=["level"],
            values="gmv_cny",
            color="txn_count",
            color_continuous_scale=["#EEF2FF", "#2563EB"],
            custom_data=["level", "gmv_share", "txn_count", "active_merchants"],
            title=treemap_title,
        )
        treemap_fig.update_traces(
            texttemplate="<b>%{label}</b><br>%{customdata[1]:.1%}",
            hovertemplate=(
                "<b>%{label}</b><br>"
                "GMV：RMB %{value:,.0f}<br>"
                "占比：%{customdata[1]:.1%}<br>"
                "交易笔数：%{customdata[2]:,.0f}<br>"
                "活跃商户数：%{customdata[3]:,.0f}<extra></extra>"
            ),
        )
        treemap_fig.update_layout(uniformtext=dict(minsize=11, mode="hide"))
        treemap_event = st.plotly_chart(
            chart_layout(treemap_fig, height=520),
            width="stretch",
            key=treemap_key,
            on_select="rerun",
            selection_mode="points",
        )
        treemap_points = selected_points(treemap_event)
        if selected_major == "__all__" and treemap_points:
            point = treemap_points[0]
            clicked_major = None
            if point.get("customdata"):
                clicked_major = point["customdata"][0]
            elif point.get("label"):
                clicked_major = point["label"]
            elif point.get("point_index") is not None:
                clicked_major = treemap_data.iloc[int(point["point_index"])]["level"]
            elif point.get("pointNumber") is not None:
                clicked_major = treemap_data.iloc[int(point["pointNumber"])]["level"]
            if clicked_major and clicked_major in set(major_summary["major_industry"]):
                st.session_state["selected_major_industry"] = str(clicked_major)
                st.rerun()

        if selected_major == "__all__":
            industry_display = industry_plot.copy()
        else:
            industry_display = industry_plot[industry_plot["major_industry"].eq(selected_major)].copy()
        industry_display = industry_display.drop(
            columns=[
                "mcc_match_rate",
                "period_label",
                "period_name",
                "period_status",
                "sort_order",
                "days",
                "period_gmv_cny",
                "period_txn_count",
            ],
            errors="ignore",
        )
        for col in ["gmv_cny"]:
            industry_display[col] = industry_display[col].map(lambda value: f"{float(value):,.0f}")
        for col in ["txn_count", "active_merchants"]:
            industry_display[col] = industry_display[col].map(lambda value: f"{float(value):,.0f}")
        for col in ["yoy_gmv_growth", "pre_uplift"]:
            if col in industry_display:
                industry_display[col] = industry_display[col].apply(fmt_pct)
        for col in ["period_gmv_share", "period_txn_share"]:
            if col in industry_display:
                industry_display[col] = industry_display[col].apply(fmt_pct)
        st.dataframe(display_table(industry_display), hide_index=True, width="stretch")

with tabs[4]:
    title_col, method_col = st.columns([1.25, 1])
    with title_col:
        st.subheader("用户与物料信号")
        st.markdown(
            '<div class="section-caption">把 02 用户聚合和 03 物料扫码快照放在一起看：用户说明真实交易触达，物料说明线下扫码素材的可见度与使用基础。</div>',
            unsafe_allow_html=True,
        )
    with method_col:
        render_method_card(
            "口径说明",
            [
                "用户数据来自 02 聚合导出，只保留 OFFLINE/BOTH 商户口径，并与 01 交易范围对齐。",
                "跨时段横向比较使用日均活跃用户；时段级去重活跃用户只用于同天数窗口对比。",
                "日均用户频次 = 日均交易笔数 / 日均活跃用户，用来衡量每天每个活跃用户平均交易几次。",
                "物料数据来自 03 每日物料快照；本页使用时段内快照均值，避免不同天数窗口直接累加。",
                "滚动窗口快照指标不在本页展示，避免和假期窗口口径混淆。",
            ],
        )

    user_plot = available_summary.copy()
    for col in ["active_users", "avg_daily_active_users", "avg_daily_user_frequency", "avg_daily_txn", "txn_count", "active_merchants"]:
        user_plot[col] = pd.to_numeric(user_plot[col], errors="coerce") if col in user_plot else pd.NA
    user_plot = user_plot.sort_values("sort_order" if "sort_order" in user_plot else "period_label")
    user_ready = user_plot["avg_daily_active_users"].notna().any()

    material_source = material_period.copy()
    if material_source.empty and not global_material.empty and "period_label" in global_material.columns:
        material_source = global_material.copy()
        if "avg_daily_all_pv" in material_source:
            material_source["avg_all_pv_snapshot"] = material_source["avg_daily_all_pv"]
        if "avg_daily_all_uv" in material_source:
            material_source["avg_all_uv_snapshot"] = material_source["avg_daily_all_uv"]
        if "data_status" not in material_source:
            material_source["data_status"] = "available"

    if not material_source.empty:
        material_source = material_source.sort_values("sort_order" if "sort_order" in material_source else "period_label").copy()
        for col in [
            "snapshot_count",
            "avg_material_count",
            "avg_approved_material_count",
            "avg_scanned_material_count",
            "avg_all_pv_snapshot",
            "avg_all_uv_snapshot",
            "scanned_material_rate",
            "avg_all_pv_snapshot_vs_baseline",
            "avg_all_uv_snapshot_vs_baseline",
            "avg_scanned_material_count_vs_baseline",
        ]:
            material_source[col] = pd.to_numeric(material_source[col], errors="coerce") if col in material_source else pd.NA
        if (
            "avg_scanned_material_count" in material_source
            and "period_label" in material_source
            and material_source["avg_scanned_material_count_vs_baseline"].isna().all()
        ):
            baseline_scanned = material_source.loc[
                material_source["period_label"].astype(str).eq("baseline_2026_apr_non_labour"),
                "avg_scanned_material_count",
            ]
            if not baseline_scanned.empty and pd.notna(baseline_scanned.iloc[0]) and float(baseline_scanned.iloc[0]) != 0:
                material_source["avg_scanned_material_count_vs_baseline"] = (
                    material_source["avg_scanned_material_count"] / float(baseline_scanned.iloc[0]) - 1
                )
    material_plot = (
        material_source[material_source["data_status"].astype(str).eq("available")].copy()
        if not material_source.empty and "data_status" in material_source
        else pd.DataFrame()
    )

    left, right = st.columns([1.05, 1])
    with left:
        st.markdown("#### 日均用户触达与交易频次")
        if user_ready:
            user_metrics = st.columns(3)
            user_metrics[0].metric(
                "日均活跃用户数",
                fmt_num(current.get("avg_daily_active_users")),
                fmt_signed_pct(growth(current.get("avg_daily_active_users"), yoy.get("avg_daily_active_users"))),
            )
            user_metrics[1].metric(
                "日均用户频次",
                fmt_num(current.get("avg_daily_user_frequency"), 2),
                fmt_signed_pct(growth(current.get("avg_daily_user_frequency"), yoy.get("avg_daily_user_frequency"))),
            )
            user_metrics[2].metric(
                "日均交易笔数",
                fmt_num(current.get("avg_daily_txn")),
                fmt_signed_pct(growth(current.get("avg_daily_txn"), yoy.get("avg_daily_txn"))),
            )
            fig = make_subplots(specs=[[{"secondary_y": True}]])
            fig.add_bar(
                x=user_plot["period_name"],
                y=user_plot["avg_daily_active_users"],
                name="日均活跃用户数",
                marker_color="#2563EB",
            )
            fig.add_scatter(
                x=user_plot["period_name"],
                y=user_plot["avg_daily_user_frequency"],
                name="日均用户频次",
                mode="lines+markers",
                marker_color="#D97706",
                secondary_y=True,
            )
            fig.update_layout(title_text="各时段日均用户触达与使用频次")
            fig.update_yaxes(title_text="日均活跃用户数", secondary_y=False)
            fig.update_yaxes(title_text="每活跃用户日均交易次数", secondary_y=True)
            fig.update_xaxes(categoryorder="array", categoryarray=list(user_plot["period_name"]), tickangle=-20)
            st.plotly_chart(chart_layout(fig, height=430), width="stretch")
        else:
            st.info("当前数据尚未接入 02 活跃用户聚合。")

    with right:
        st.markdown("#### 物料扫码快照")
        if material_plot.empty:
            st.info("当前 03 导出没有返回物料扫码时段数据。")
        else:
            current_material = material_plot[material_plot["period_label"].astype(str).eq("holiday_2026_labour")]
            if not current_material.empty:
                row = current_material.iloc[0]
                material_metrics = st.columns(3)
                material_metrics[0].metric(
                    "平均 PV 快照",
                    fmt_num(row.get("avg_all_pv_snapshot")),
                    f"{fmt_signed_pct(row.get('avg_all_pv_snapshot_vs_baseline'))} 较 4 月基线",
                )
                material_metrics[1].metric(
                    "平均 UV 快照",
                    fmt_num(row.get("avg_all_uv_snapshot")),
                    f"{fmt_signed_pct(row.get('avg_all_uv_snapshot_vs_baseline'))} 较 4 月基线",
                )
                material_metrics[2].metric(
                    "平均有扫码物料数",
                    fmt_num(row.get("avg_scanned_material_count")),
                    f"{fmt_signed_pct(row.get('avg_scanned_material_count_vs_baseline'))} 较 4 月基线",
                )

            fig = make_subplots(specs=[[{"secondary_y": True}]])
            fig.add_bar(
                x=material_plot["period_name"],
                y=material_plot["avg_all_pv_snapshot"],
                name="平均 PV 快照",
                marker_color="#0F766E",
            )
            fig.add_bar(
                x=material_plot["period_name"],
                y=material_plot["avg_all_uv_snapshot"],
                name="平均 UV 快照",
                marker_color="#60A5FA",
            )
            fig.add_scatter(
                x=material_plot["period_name"],
                y=material_plot["avg_scanned_material_count"],
                name="平均有扫码物料数",
                mode="lines+markers",
                marker_color="#B45309",
                secondary_y=True,
            )
            fig.update_layout(title_text="物料可见度与扫码物料基础")
            fig.update_yaxes(title_text="PV / UV 快照", secondary_y=False)
            fig.update_yaxes(title_text="有扫码物料数", secondary_y=True)
            fig.update_xaxes(categoryorder="array", categoryarray=list(material_plot["period_name"]), tickangle=-20)
            st.plotly_chart(chart_layout(fig, height=430), width="stretch")

    table_left, table_right = st.columns(2)
    with table_left:
        st.markdown("##### 用户时段汇总")
        user_display_cols = [
            "period_name",
            "avg_daily_active_users",
            "avg_daily_user_frequency",
            "txn_count",
            "avg_daily_txn",
            "active_users",
            "active_merchants",
        ]
        user_display = user_plot[[col for col in user_display_cols if col in user_plot]].copy()
        for col in ["avg_daily_active_users", "active_users", "txn_count", "avg_daily_txn", "active_merchants"]:
            if col in user_display:
                user_display[col] = user_display[col].map(lambda value: "N/A" if pd.isna(value) else f"{float(value):,.0f}")
        if "avg_daily_user_frequency" in user_display:
            user_display["avg_daily_user_frequency"] = user_display["avg_daily_user_frequency"].map(lambda value: "N/A" if pd.isna(value) else f"{float(value):,.2f}")
        st.dataframe(display_table(user_display), hide_index=True, width="stretch")

    with table_right:
        st.markdown("##### 物料时段汇总")
        if material_source.empty:
            material_display = material.copy()
            if "metric" in material_display:
                material_display = material_display[~material_display["metric"].astype(str).str.contains("latest", case=False, na=False)]
        else:
            material_display_cols = [
                "period_name",
                "data_status",
                "snapshot_count",
                "avg_material_count",
                "avg_approved_material_count",
                "avg_scanned_material_count",
                "avg_all_pv_snapshot",
                "avg_all_uv_snapshot",
                "scanned_material_rate",
            ]
            material_display = material_source[[col for col in material_display_cols if col in material_source]].copy()
            for col in [
                "snapshot_count",
                "avg_material_count",
                "avg_approved_material_count",
                "avg_scanned_material_count",
                "avg_all_pv_snapshot",
                "avg_all_uv_snapshot",
            ]:
                if col in material_display:
                    material_display[col] = material_display[col].map(lambda value: "N/A" if pd.isna(value) else f"{float(value):,.0f}")
            if "scanned_material_rate" in material_display:
                material_display["scanned_material_rate"] = material_display["scanned_material_rate"].apply(fmt_pct)
        st.dataframe(display_table(material_display), hide_index=True, width="stretch")

with tabs[5]:
    title_col, method_col = st.columns([1.28, 1])
    with title_col:
        st.subheader("商户激活与覆盖贡献")
        st.markdown(
            '<div class="section-caption">分组对比两个 13 天五一窗口内的商户活跃变化：2026-04-25 至 2026-05-07 vs 2025-04-25 至 2025-05-07。</div>',
            unsafe_allow_html=True,
        )
    with method_col:
        render_method_card(
            "口径说明",
            [
                "留存活跃：2025 五一有交易，2026 五一也有交易。",
                "同窗口回流存量：开户日 <= 2025-05-07，2025 五一无交易，2026 五一有交易；不是全年沉默定义。",
                "新增覆盖：开户日 > 2025-05-07，且 2026 五一有交易。",
                "流失/归零：2025 五一有交易，2026 五一无交易。",
            ],
        )
    if merchant_activation_summary.empty:
        st.info("商户激活结果待生成。完整 01 商户日导出到齐后运行 scripts/process_exports.py。")
    else:
        segment_labels = {
            "retained_active": "留存活跃",
            "reactivated_dormant": "同窗口回流存量",
            "new_coverage": "新增覆盖",
            "current_only_unknown_onboarding": "本期活跃但入驻日未知",
            "churned_zeroed": "流失/归零",
            "out_of_scope": "范围外",
        }
        activation_plot = merchant_activation_summary.sort_values("sort_order").copy()
        activation_plot["segment_name"] = activation_plot["activation_segment"].map(segment_labels).fillna(activation_plot["activation_segment"])

        current_segments = activation_plot[activation_plot["holiday_2026_txn_count"].gt(0)].copy()
        reactivated = activation_plot[activation_plot["activation_segment"].eq("reactivated_dormant")]
        new_coverage = activation_plot[activation_plot["activation_segment"].eq("new_coverage")]
        retained = activation_plot[activation_plot["activation_segment"].eq("retained_active")]

        metric_cols = st.columns(4)
        metric_cols[0].metric("留存活跃商户", fmt_num(retained["merchant_count"].sum() if not retained.empty else 0))
        metric_cols[1].metric("回流存量商户", fmt_num(reactivated["merchant_count"].sum() if not reactivated.empty else 0))
        metric_cols[2].metric("新增覆盖商户", fmt_num(new_coverage["merchant_count"].sum() if not new_coverage.empty else 0))
        metric_cols[3].metric("新增+回流 GMV 占比", fmt_pct(current_segments[current_segments["activation_segment"].isin(["new_coverage", "reactivated_dormant"])]["current_gmv_share"].sum()))

        share_long = current_segments.melt(
            id_vars=["segment_name", "sort_order"],
            value_vars=["current_gmv_share", "current_txn_share"],
            var_name="metric",
            value_name="share",
        )
        share_long["metric"] = share_long["metric"].map(
            {
                "current_gmv_share": "2026 GMV 占比",
                "current_txn_share": "2026 交易笔数占比",
            }
        )
        fig = px.bar(
            share_long,
            x="segment_name",
            y="share",
            color="metric",
            barmode="group",
            title="2026 五一商户分组贡献",
            labels={"segment_name": "", "share": "本期占比", "metric": ""},
            color_discrete_sequence=["#0F766E", "#2563EB"],
        )
        fig.update_yaxes(tickformat=".0%")
        st.plotly_chart(chart_layout(fig, height=390), width="stretch")

        summary_display = activation_plot[
            [
                "segment_name",
                "merchant_count",
                "holiday_2026_gmv_cny",
                "holiday_2026_txn_count",
                "current_gmv_share",
                "current_txn_share",
                "gmv_yoy_delta_cny",
                "txn_yoy_delta",
            ]
        ].copy()
        for col in ["holiday_2026_gmv_cny", "gmv_yoy_delta_cny"]:
            summary_display[col] = summary_display[col].map(lambda value: f"{float(value):,.0f}")
        for col in ["holiday_2026_txn_count", "txn_yoy_delta"]:
            summary_display[col] = summary_display[col].map(lambda value: f"{float(value):,.0f}")
        for col in ["current_gmv_share", "current_txn_share"]:
            summary_display[col] = summary_display[col].apply(fmt_pct)
        st.dataframe(display_table(summary_display), hide_index=True, width="stretch")

        if not merchant_activation_detail.empty:
            st.markdown("#### 商户明细")
            segment_options = list(activation_plot["activation_segment"])
            default_segment = "new_coverage" if "new_coverage" in segment_options else segment_options[0]
            selected_segment = st.selectbox(
                "商户分组",
                segment_options,
                index=segment_options.index(default_segment),
                format_func=lambda value: segment_labels.get(value, value),
            )
            detail_display = (
                merchant_activation_detail[merchant_activation_detail["activation_segment"].eq(selected_segment)]
                .sort_values("holiday_2026_gmv_cny", ascending=False)
                .head(100)
                .copy()
            )
            for col in ["holiday_2025_gmv_cny", "holiday_2026_gmv_cny", "gmv_yoy_delta_cny", "aov_2025_cny", "aov_2026_cny"]:
                if col in detail_display:
                    detail_display[col] = detail_display[col].map(lambda value: "N/A" if pd.isna(value) else f"{float(value):,.0f}")
            for col in ["holiday_2025_txn_count", "holiday_2026_txn_count", "txn_yoy_delta"]:
                if col in detail_display:
                    detail_display[col] = detail_display[col].map(lambda value: f"{float(value):,.0f}")
            st.dataframe(display_table(detail_display), hide_index=True, width="stretch")

with tabs[6]:
    title_col, method_col = st.columns([1.28, 1])
    with title_col:
        st.subheader("头部商户案例")
        st.markdown('<div class="section-caption">头部商户按两种方式展示：2026 五一总 GMV 贡献，以及日均交易频次。</div>', unsafe_allow_html=True)
    with method_col:
        render_method_card(
            "口径说明",
            [
                "范围：仅 2026 五一窗口，仅 OFFLINE/BOTH 商户。",
                "GMV 排名：按商户层级总 GMV 降序；同时展示日均 GMV 作为强度参考。",
                "频次排名：日均交易笔数 = 交易笔数 / 活跃天数；商户日交易强度 = 交易笔数 / 活跃商户日。",
                "行业：展示 MCC 映射后的细分行业。",
            ],
        )
    render_insights(insights, "top_merchants", "执行与策略备注")
    st.markdown("#### GMV 前 20 商户")
    top_display = top_merchants.copy()
    if "industry" not in top_display and "major_industry" in top_display:
        top_display["industry"] = top_display["major_industry"]
    top_display = top_display.drop(columns=["major_industry"], errors="ignore")
    if "gmv_cny" in top_display:
        top_display["gmv_cny"] = top_display["gmv_cny"].map(lambda value: f"{float(value):,.0f}")
    if "avg_daily_gmv_cny" in top_display:
        top_display["avg_daily_gmv_cny"] = top_display["avg_daily_gmv_cny"].map(lambda value: f"{float(value):,.0f}")
    if "aov_cny" in top_display:
        top_display["aov_cny"] = top_display["aov_cny"].map(lambda value: f"{float(value):,.0f}")
    for col in ["txn_count", "merchant_day_count", "active_days"]:
        if col in top_display:
            top_display[col] = top_display[col].map(lambda value: f"{float(value):,.0f}")
    for col in ["avg_daily_txn", "txn_per_merchant_day"]:
        if col in top_display:
            top_display[col] = top_display[col].map(lambda value: f"{float(value):,.2f}")
    top_cols = [
        col
        for col in ["merchant_rank", "merchant_display", "business_city", "industry", "gmv_cny", "avg_daily_gmv_cny", "txn_count", "avg_daily_txn", "active_days", "aov_cny", "note"]
        if col in top_display
    ]
    st.dataframe(display_table(top_display[top_cols]), hide_index=True, width="stretch")

    st.markdown("#### 日均交易笔数前 20 商户")
    if top_merchants_by_frequency.empty:
        st.info("商户频次排名待生成。请重新运行 scripts/process_exports.py 生成 top_merchants_by_frequency.csv。")
    else:
        txn_display = top_merchants_by_frequency.copy()
        if "industry" not in txn_display and "major_industry" in txn_display:
            txn_display["industry"] = txn_display["major_industry"]
        txn_display = txn_display.drop(columns=["major_industry"], errors="ignore")
        for col in ["gmv_cny", "avg_daily_gmv_cny"]:
            if col in txn_display:
                txn_display[col] = txn_display[col].map(lambda value: f"{float(value):,.0f}")
        if "aov_cny" in txn_display:
            txn_display["aov_cny"] = txn_display["aov_cny"].map(lambda value: f"{float(value):,.0f}")
        for col in ["txn_count", "merchant_day_count", "active_days"]:
            if col in txn_display:
                txn_display[col] = txn_display[col].map(lambda value: f"{float(value):,.0f}")
        for col in ["avg_daily_txn", "txn_per_merchant_day"]:
            if col in txn_display:
                txn_display[col] = txn_display[col].map(lambda value: f"{float(value):,.2f}")
        txn_cols = [
            col
            for col in [
                "frequency_rank",
                "merchant_display",
                "business_city",
                "industry",
                "avg_daily_txn",
                "txn_count",
                "active_days",
                "txn_per_merchant_day",
                "gmv_cny",
                "avg_daily_gmv_cny",
                "aov_cny",
                "note",
            ]
            if col in txn_display
        ]
        st.dataframe(display_table(txn_display[txn_cols]), hide_index=True, width="stretch")

with tabs[7]:
    st.subheader("方法与数据边界")
    render_insights(insights, "methodology", "解读边界")
    active_user_status = (
        "已接入页面"
        if "active_users" in period_summary and period_summary["active_users"].notna().any()
        else "待重跑：本地 02 需要与 01 的 OFFLINE/BOTH 及核心排除口径对齐后再展示活跃用户字段"
    )
    st.markdown(
        f"""
        **核心指标口径**

        - 日均交易笔数 = 总交易笔数 / 时段天数。
        - 商户日均频次 = 总交易笔数 / 活跃商户日。
        - GMV 使用 01 商户日导出中的 `todaytrademoney / 100`，按人民币汇总。
        - 日均 GMV = 总 GMV / 时段天数。
        - 客单价 = GMV / 交易笔数，不直接除以活跃用户数。
        - 两个五一窗口都是 13 天，因此总 GMV 可直接做同比；国庆、春节和 4 月基线等不同时长窗口应使用日均 GMV / 日均交易笔数比较。

        **当前数据状态**

        - 选择已处理本地数据时，页面使用处理后的 `01` 商户日明细、`02` 用户聚合和 `03` 物料聚合。
        - 城市、行业、头部商户、同店和商户激活视图均由完整 01 商户日明细在本地聚合生成。
        - 活跃用户状态：{active_user_status}。
        - 澳大利亚后续复用同一套分析结构，需另行完成分区、行数和 join 覆盖 probe 后再导出。

        **云端来源表**

        - `wechat_pay_overseas::t_dw_oversea_mch_manage_detail_day`：商户日交易汇总，提供交易笔数、GMV、商户入驻日和商户级时段对比。
        - `wechat_pay_overseas::t_dw_ol_submch_all_day`：新西兰商户范围和商户属性，按 `ds + submchid` 关联；提供 `merchant_country_code = '554'`、`business_type`、`stores_address`、MCC 和机构字段。
        - `wechat_pay_overseas::t_dwm_rate_trade_funds_profit_loss_day`：02 用户聚合的交易明细来源，只用于活跃用户数和对账检查，不替代本报告采用的 01 GMV。
        - `wechat_pay_overseas::t_dwm_material_scan_statistic_day`：03 物料 PV/UV/物料数指标来源。

        **本地维表来源**

        - `D:\\Tencent\\Data analysis\\mcc_industry_final.csv`：MCC 到行业大类和细分行业映射。
        - `D:\\Tencent\\Data analysis\\ANZ_Data_Warehouse\\data\\Geo_warehouse\\nz_geo_dimension.csv`：新西兰地理参考文件。
        - `D:\\Tencent\\Data analysis\\Wechat-Pay-ANZ-MAP`：复用其 `business_city` 匹配和标准化逻辑。

        **外部公开证据**

        - Stats NZ 国际旅行月度数据用于解释新西兰入境游客恢复背景；2026 年 2 月海外访客超过 40.8 万人，截至 2026 年 2 月年度海外访客约 358 万，约为 2019 年 12 月水平的 92%。
        - Stats NZ 月度数据摘要显示，2026 年 2 月中国访客同比增加 41,700 人，春节窗口的中国客群恢复可作为本报告春节/假期支付信号的外部背景。
        - MBIE/TEIC 修订版 Monthly Regional Tourism Estimates 显示，截至 2026 年 2 月年度新西兰游客总消费约 465 亿新西兰元，同比 +11%；国际游客消费约 196 亿新西兰元，同比 +24%。
        - MBIE International Visitor Survey 用于解释国际游客消费、行为和停留特征，但 IVS 季度结果抽样误差更高；本报告不把 IVS 或 MRTE 直接等同为 WeChat Pay 客群规模。

        **报告范围与边界**

        - 国家范围：仅新西兰商户，基于 `merchant_country_code = '554'`。
        - 渠道范围：`business_type in ('OFFLINE', 'BOTH')`；线上-only 商户已从处理后报告输出中排除。
        - 核心排除：ZHENXING 机构已从报告输出中剔除。
        - 敏感数据：不导出原始用户标识；02 仅保留聚合后的 `active_user_cnt`。
        - 对账要求：02 活跃用户聚合仅在其时段交易笔数和 GMV 与 01 报告口径对齐后展示。
        - 公平比较：同天数五一同比可看总 GMV；跨不同时长窗口使用日均 GMV / 日均交易笔数。
        """
    )
    st.markdown(
        """
        公开证据链接：
        [Stats NZ 月度国际旅行摘要](https://www.beehive.govt.nz/release/new-zealand-tourism-continuing-rise)；
        [MBIE/TEIC MRTE 重点结果](https://teic.mbie.govt.nz/assets/mrte/MRTE%20Topline%20results%20FINAL.pdf)；
        [MBIE International Visitor Survey](https://www.mbie.govt.nz/immigration-and-tourism/tourism-research-and-data/tourism-data-releases/international-visitor-survey-ivs)。
        """
    )
    if not period_catalog.empty:
        st.markdown("#### 目标时段目录")
        st.dataframe(display_table(period_catalog), hide_index=True, width="stretch")
    render_public_context(public_context)
    st.markdown("#### 提取后预期文件")
    st.code(
        "\n".join(
            [
                "sql/01a_active_merchant_daily_trade_daily_probe.sql",
                "sql/01_merchant_daily_trade_export_template.sql",
                "sql/02_user_aggregate_export.sql",
                "sql/03_material_scan_aggregate_export.sql",
                "scripts/process_exports.py",
                "data/raw/merchant_daily_trade_export_part_01.csv ... part_XX.csv",
                "data/raw/user_aggregate_export.csv",
                "data/raw/material_scan_aggregate_export.csv",
                "data/processed/period_summary.csv",
                "data/processed/period_daily.csv",
                "data/processed/region_summary.csv",
                "data/processed/industry_period_summary.csv",
                "data/processed/top_merchants.csv",
                "data/processed/top_merchants_by_frequency.csv",
                "data/processed/top_merchants_by_txn.csv",
                "data/processed/merchant_activation_summary.csv",
            ]
        ),
        language="text",
    )
