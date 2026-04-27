"""
호텔 더본 제주 — 운영 현황 대시보드
Streamlit + Google Sheets 실시간 연동
"""

import streamlit as st
import gspread
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from google.oauth2.service_account import Credentials
from datetime import datetime
import time

# ─────────────────────────────────────────────
# 페이지 기본 설정
# ─────────────────────────────────────────────
st.set_page_config(
    page_title="호텔 더본 제주 | 운영 대시보드",
    page_icon="🏨",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ─────────────────────────────────────────────
# CSS 스타일
# ─────────────────────────────────────────────
st.markdown("""
<style>
    /* 전체 폰트 */
    html, body, [class*="css"] {
        font-family: 'Noto Sans KR', 'Apple SD Gothic Neo', sans-serif;
    }
    /* 메인 배경 */
    .stApp { background-color: #F8F8F6; }
    /* 헤더 영역 */
    .main-header {
        background: #1a1a2e;
        color: white;
        padding: 1.5rem 2rem;
        border-radius: 12px;
        margin-bottom: 1.5rem;
    }
    .main-header h1 { margin: 0; font-size: 1.4rem; font-weight: 600; }
    .main-header p { margin: 4px 0 0; font-size: 0.8rem; opacity: 0.65; }
    /* KPI 카드 */
    .kpi-card {
        background: white;
        border-radius: 10px;
        padding: 1.25rem 1.5rem;
        border: 1px solid #EBEBEB;
        height: 100%;
    }
    .kpi-label { font-size: 0.72rem; color: #888; margin: 0 0 6px; font-weight: 500; letter-spacing: 0.05em; text-transform: uppercase; }
    .kpi-value { font-size: 1.8rem; font-weight: 700; margin: 0; color: #1a1a2e; }
    .kpi-delta-pos { font-size: 0.75rem; color: #2d8f5e; margin: 4px 0 0; }
    .kpi-delta-neg { font-size: 0.75rem; color: #c0392b; margin: 4px 0 0; }
    .kpi-delta-neu { font-size: 0.75rem; color: #888; margin: 4px 0 0; }
    /* 섹션 카드 */
    .section-card {
        background: white;
        border-radius: 10px;
        padding: 1.25rem 1.5rem;
        border: 1px solid #EBEBEB;
        margin-bottom: 1rem;
    }
    /* 로그인 영역 */
    .login-container {
        max-width: 400px;
        margin: 8rem auto;
        background: white;
        border-radius: 16px;
        padding: 2.5rem;
        border: 1px solid #EBEBEB;
        box-shadow: 0 4px 24px rgba(0,0,0,0.06);
    }
    /* 알림 배지 */
    .badge-red { background: #fdecea; color: #c0392b; padding: 2px 8px; border-radius: 20px; font-size: 0.7rem; font-weight: 600; }
    .badge-green { background: #e8f5e9; color: #2d8f5e; padding: 2px 8px; border-radius: 20px; font-size: 0.7rem; font-weight: 600; }
    .badge-blue { background: #e3eeff; color: #1a5fb4; padding: 2px 8px; border-radius: 20px; font-size: 0.7rem; font-weight: 600; }
    /* Plotly 차트 배경 */
    .js-plotly-plot { border-radius: 8px; }
    /* 구분선 */
    .divider { border: none; border-top: 1px solid #EBEBEB; margin: 1.5rem 0; }
    /* 숨기기 */
    #MainMenu, footer, header { visibility: hidden; }
    .block-container { padding-top: 1.5rem; padding-bottom: 1.5rem; }
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# 색상 팔레트
# ─────────────────────────────────────────────
COLORS = {
    "navy":   "#1a1a2e",
    "blue":   "#3266ad",
    "teal":   "#1D9E75",
    "amber":  "#BA7517",
    "coral":  "#D85A30",
    "gray":   "#888780",
    "light":  "#F8F8F6",
    "red":    "#c0392b",
    "green":  "#2d8f5e",
}

PLOTLY_LAYOUT = dict(
    paper_bgcolor="white",
    plot_bgcolor="white",
    font=dict(family="Noto Sans KR, Apple SD Gothic Neo, sans-serif", size=12, color="#333"),
    margin=dict(l=10, r=10, t=30, b=10),
    xaxis=dict(gridcolor="#F0F0F0", showgrid=False, linecolor="#E0E0E0"),
    yaxis=dict(gridcolor="#F0F0F0", showgrid=True, linecolor="#E0E0E0"),
)

# ─────────────────────────────────────────────
# 로그인 처리
# ─────────────────────────────────────────────
def check_password():
    """비밀번호 보호 — secrets.toml의 password 값과 비교"""
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False

    if st.session_state.authenticated:
        return True

    # 로그인 화면
    col1, col2, col3 = st.columns([1, 1.2, 1])
    with col2:
        st.markdown("""
        <div style="text-align:center; margin-top:4rem; margin-bottom:2rem;">
            <div style="font-size:2.5rem;">🏨</div>
            <h2 style="color:#1a1a2e; font-weight:700; margin:.5rem 0 .25rem;">호텔 더본 제주</h2>
            <p style="color:#888; font-size:.85rem; margin:0;">운영 현황 대시보드 — 내부 전용</p>
        </div>
        """, unsafe_allow_html=True)

        with st.form("login_form"):
            pw = st.text_input(
                "비밀번호를 입력하세요",
                type="password",
                placeholder="비밀번호",
                label_visibility="collapsed"
            )
            submitted = st.form_submit_button("입장하기", use_container_width=True, type="primary")

        if submitted:
            if pw == st.secrets.get("password", ""):
                st.session_state.authenticated = True
                st.rerun()
            else:
                st.error("비밀번호가 올바르지 않습니다.")

        st.markdown("""
        <p style="text-align:center; color:#aaa; font-size:.72rem; margin-top:1.5rem;">
            접근 권한 문의: 호텔사업팀 팀장
        </p>
        """, unsafe_allow_html=True)
    return False

# ─────────────────────────────────────────────
# 구글 시트 연결
# ─────────────────────────────────────────────
SHEET_ID = "1ZBLBogPNFKNm9j-haqSD2RDQMG2MqDf2QB694LGXFDs"  # ← 실제 시트 ID

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets.readonly",
    "https://www.googleapis.com/auth/drive.readonly",
]

@st.cache_resource(ttl=300)  # 5분마다 재연결
def get_gsheet_client():
    """서비스 계정으로 구글 시트 클라이언트 생성"""
    try:
        creds = Credentials.from_service_account_info(
            st.secrets["gcp_service_account"],
            scopes=SCOPES
        )
        client = gspread.authorize(creds)
        return client
    except Exception as e:
        st.error(f"구글 시트 연결 오류: {e}")
        return None

@st.cache_data(ttl=300)  # 5분마다 데이터 갱신
def load_sheet_data(sheet_id: str, worksheet_name: str = None):
    """구글 시트에서 워크시트 전체 데이터 로드"""
    try:
        client = get_gsheet_client()
        if client is None:
            return None
        spreadsheet = client.open_by_key(sheet_id)
        if worksheet_name:
            ws = spreadsheet.worksheet(worksheet_name)
        else:
            ws = spreadsheet.sheet1
        records = ws.get_all_values()
        return records
    except Exception as e:
        st.error(f"데이터 로드 오류: {e}")
        return None

# ─────────────────────────────────────────────
# 기준 데이터 (구글 시트에서 읽어오지 못할 경우 폴백용)
# — 시트 구조에 맞게 파싱 함수를 수정해 사용하세요 —
# ─────────────────────────────────────────────
BASE_YEARLY = {
    "연도": ["2017","2018","2019","2020","2021","2022","2023","2024","2025"],
    "총매출":    [39.2, 51.2, 58.9, 61.7, 68.1, 92.1, 92.9, 88.1, 76.4],
    "객실매출":  [23.3, 29.2, 36.8, 38.8, 41.8, 55.7, 60.5, 64.9, 60.3],
    "음식매출":  [10.5, 15.0, 18.4, 18.5, 22.3, 31.4, 27.0, 17.0, 10.1],
    "순이익":    [-7.8,  0.7,  2.7,  2.9,  0.3,  7.1,  8.8,  8.5,  4.3],
    "점유율":    [85.8, 96.2, 97.3, 95.7, 88.9, 96.8, 96.0, 95.9, 91.8],
    "평균단가":  [55.3, 60.9, 76.1, 81.3, 95.4,115.8,126.3,134.1,129.1],
}

# ─────────────────────────────────────────────
# 구글 시트 파싱 — 점유율 시트 (매일 업데이트)
# 시트 구조: A열=날짜, B열=점유율, C열=객실매출 (예시)
# ★ 실제 시트 컬럼 구조에 맞게 수정하세요 ★
# ─────────────────────────────────────────────
def parse_occupancy_sheet(raw_data):
    """
    구글 시트 점유율 탭 파싱
    예상 형식:
      Row 0 (헤더): [날짜, 점유율, 객실매출, 비고]
      Row 1~: [2026-01-01, 84.6, 383127011, ...]
    """
    if not raw_data or len(raw_data) < 2:
        return None
    try:
        df = pd.DataFrame(raw_data[1:], columns=raw_data[0])
        # 컬럼명 정리 (앞뒤 공백 제거)
        df.columns = [c.strip() for c in df.columns]
        # 빈 행 제거
        df = df[df.iloc[:, 0] != ""]
        return df
    except Exception as e:
        st.warning(f"점유율 데이터 파싱 오류: {e}")
        return None

def parse_monthly_sheet(raw_data):
    """
    월별 실적 시트 파싱
    예상 형식:
      Row 0 (헤더): [연도, 1월, 2월, ..., 12월, 합계]
      Row 1~: 연도별 데이터
    """
    if not raw_data or len(raw_data) < 2:
        return None
    try:
        df = pd.DataFrame(raw_data[1:], columns=raw_data[0])
        df.columns = [c.strip() for c in df.columns]
        df = df[df.iloc[:, 0] != ""]
        return df
    except Exception as e:
        st.warning(f"월별 데이터 파싱 오류: {e}")
        return None

# ─────────────────────────────────────────────
# KPI 카드 컴포넌트
# ─────────────────────────────────────────────
def kpi_card(label, value, delta=None, delta_type="neu", suffix=""):
    delta_class = {"pos": "kpi-delta-pos", "neg": "kpi-delta-neg", "neu": "kpi-delta-neu"}.get(delta_type, "kpi-delta-neu")
    delta_html = f'<p class="{delta_class}">{delta}</p>' if delta else ""
    st.markdown(f"""
    <div class="kpi-card">
        <p class="kpi-label">{label}</p>
        <p class="kpi-value">{value}{suffix}</p>
        {delta_html}
    </div>
    """, unsafe_allow_html=True)

# ─────────────────────────────────────────────
# 차트: 연도별 매출 추이
# ─────────────────────────────────────────────
def chart_yearly_revenue(df_yearly):
    fig = make_subplots(specs=[[{"secondary_y": True}]])

    years = df_yearly["연도"]

    fig.add_trace(go.Bar(
        name="총매출", x=years, y=df_yearly["총매출"],
        marker_color=COLORS["blue"], opacity=0.7,
        marker_line_width=0, width=0.25,
        hovertemplate="%{x}년<br>총매출: %{y:.1f}억원<extra></extra>"
    ), secondary_y=False)

    fig.add_trace(go.Bar(
        name="객실매출", x=years, y=df_yearly["객실매출"],
        marker_color=COLORS["teal"], opacity=0.75,
        marker_line_width=0, width=0.25,
        hovertemplate="%{x}년<br>객실매출: %{y:.1f}억원<extra></extra>"
    ), secondary_y=False)

    fig.add_trace(go.Bar(
        name="음식매출", x=years, y=df_yearly["음식매출"],
        marker_color=COLORS["amber"], opacity=0.75,
        marker_line_width=0, width=0.25,
        hovertemplate="%{x}년<br>음식매출: %{y:.1f}억원<extra></extra>"
    ), secondary_y=False)

    fig.add_trace(go.Scatter(
        name="순이익", x=years, y=df_yearly["순이익"],
        mode="lines+markers",
        line=dict(color=COLORS["coral"], width=2.5, dash="solid"),
        marker=dict(size=7, color=COLORS["coral"]),
        hovertemplate="%{x}년<br>순이익: %{y:.1f}억원<extra></extra>"
    ), secondary_y=True)

    fig.update_layout(
        paper_bgcolor="white",
        plot_bgcolor="white",
        font=dict(family="Noto Sans KR, sans-serif", size=12, color="#333"),
        barmode="group",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1, font_size=11),
        height=300,
        yaxis_title="억원",
        yaxis2_title="순이익(억원)",
        yaxis=dict(gridcolor="#F5F5F5"),
        yaxis2=dict(gridcolor="rgba(0,0,0,0)"),
        hovermode="x unified",
    )
    return fig

# ─────────────────────────────────────────────
# 차트: 점유율 & 평균단가 추이
# ─────────────────────────────────────────────
def chart_occ_adr(df_yearly):
    fig = make_subplots(specs=[[{"secondary_y": True}]])

    years = df_yearly["연도"]

    fig.add_trace(go.Bar(
        name="점유율(%)", x=years, y=df_yearly["점유율"],
        marker_color=COLORS["blue"], opacity=0.18,
        marker_line_color=COLORS["blue"], marker_line_width=1.5,
        hovertemplate="%{x}년<br>점유율: %{y:.1f}%<extra></extra>"
    ), secondary_y=False)

    fig.add_trace(go.Scatter(
        name="평균단가(천원)", x=years, y=df_yearly["평균단가"],
        mode="lines+markers",
        line=dict(color=COLORS["amber"], width=2.5),
        marker=dict(size=6, color=COLORS["amber"]),
        hovertemplate="%{x}년<br>평균단가: %{y:.1f}천원<extra></extra>"
    ), secondary_y=True)

    fig.update_layout(
        paper_bgcolor="white",
        plot_bgcolor="white",
        font=dict(family="Noto Sans KR, sans-serif", size=12, color="#333"),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1, font_size=11),
        height=260,
        yaxis=dict(title="점유율(%)", range=[70, 105], gridcolor="#F5F5F5"),
        yaxis2=dict(title="평균단가(천원)", gridcolor="rgba(0,0,0,0)"),
        hovermode="x unified",
    )
    return fig

# ─────────────────────────────────────────────
# 차트: 실적 vs 목표 (2026)
# ─────────────────────────────────────────────
def chart_actual_vs_target(monthly_data: dict):
    months = list(monthly_data.keys())
    actual = [v["실적"] for v in monthly_data.values()]
    target = [v["목표"] for v in monthly_data.values()]
    prev   = [v["전년"] for v in monthly_data.values()]

    fig = go.Figure()

    fig.add_trace(go.Bar(
        name="실적", x=months, y=actual,
        marker_color=COLORS["blue"], marker_line_width=0, opacity=0.8,
        width=0.3,
        hovertemplate="%{x}<br>실적: %{y:.2f}억원<extra></extra>"
    ))
    fig.add_trace(go.Bar(
        name="목표(80%OCC)", x=months, y=target,
        marker_color="#D3D1C7", marker_line_width=0, opacity=0.65,
        width=0.3,
        hovertemplate="%{x}<br>목표: %{y:.2f}억원<extra></extra>"
    ))
    fig.add_trace(go.Scatter(
        name="전년 실적", x=months, y=prev,
        mode="lines+markers",
        line=dict(color=COLORS["coral"], width=2, dash="dot"),
        marker=dict(size=8, color=COLORS["coral"], symbol="diamond"),
        hovertemplate="%{x}<br>전년: %{y:.2f}억원<extra></extra>"
    ))

    fig.update_layout(
        paper_bgcolor="white",
        plot_bgcolor="white",
        font=dict(family="Noto Sans KR, sans-serif", size=12, color="#333"),
        barmode="group",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1, font_size=11),
        height=240,
        xaxis=dict(gridcolor="#F0F0F0", showgrid=False, linecolor="#E0E0E0"),
        yaxis=dict(title="억원", range=[3, 6], gridcolor="#F5F5F5"),
        hovermode="x unified",
    )
    return fig

# ─────────────────────────────────────────────
# 차트: 탐모라 손익
# ─────────────────────────────────────────────
def chart_tambura_pnl(data_2025: list, data_2026: list):
    months = ["1월","2월","3월","4월","5월","6월","7월","8월","9월","10월","11월","12월"]

    fig = go.Figure()
    fig.add_trace(go.Bar(
        name="2025년", x=months, y=data_2025,
        marker_color=COLORS["blue"], opacity=0.55, marker_line_width=0,
        hovertemplate="%{x}<br>2025 손익: %{y:.1f}백만원<extra></extra>"
    ))

    d26 = [v if v is not None else 0 for v in data_2026]
    colors_26 = [COLORS["coral"] if v is not None else "rgba(0,0,0,0)" for v in data_2026]
    fig.add_trace(go.Bar(
        name="2026년", x=months, y=d26,
        marker_color=colors_26, opacity=0.78, marker_line_width=0,
        hovertemplate="%{x}<br>2026 손익: %{y:.1f}백만원<extra></extra>"
    ))

    # 0선
    fig.add_hline(y=0, line_dash="solid", line_color="#CCCCCC", line_width=1)

    fig.update_layout(
        paper_bgcolor="white",
        plot_bgcolor="white",
        font=dict(family="Noto Sans KR, sans-serif", size=12, color="#333"),
        barmode="group",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1, font_size=11),
        height=240,
        yaxis=dict(title="백만원", gridcolor="#F5F5F5"),
        hovermode="x unified",
    )
    return fig

# ─────────────────────────────────────────────
# 차트: 오늘 실시간 점유율 게이지
# ─────────────────────────────────────────────
def chart_gauge(value, title, reference=95.9):
    fig = go.Figure(go.Indicator(
        mode="gauge+number+delta",
        value=value,
        delta={"reference": reference, "valueformat": ".1f", "suffix": "%p"},
        title={"text": title, "font": {"size": 13, "color": "#555"}},
        number={"suffix": "%", "font": {"size": 28, "color": COLORS["navy"]}},
        gauge={
            "axis": {"range": [0, 100], "tickwidth": 1, "tickcolor": "#ccc", "ticksuffix": "%"},
            "bar": {"color": COLORS["blue"], "thickness": 0.25},
            "bgcolor": "white",
            "borderwidth": 0,
            "steps": [
                {"range": [0, 70], "color": "#FDECEA"},
                {"range": [70, 85], "color": "#FFF3E0"},
                {"range": [85, 100], "color": "#E8F5E9"},
            ],
            "threshold": {
                "line": {"color": COLORS["coral"], "width": 2},
                "thickness": 0.8,
                "value": reference
            },
        }
    ))
    fig.update_layout(
        paper_bgcolor="white", plot_bgcolor="white",
        margin=dict(l=20, r=20, t=40, b=10),
        height=200,
        font=dict(family="Noto Sans KR, sans-serif")
    )
    return fig

# ─────────────────────────────────────────────
# 차트: 탐모라 월별 매출 & 이용객
# ─────────────────────────────────────────────
def chart_tambura_rev(revenue: list, pax: list):
    months = ["1월","2월","3월","4월","5월","6월","7월","8월","9월","10월","11월","12월"]
    fig = make_subplots(specs=[[{"secondary_y": True}]])

    fig.add_trace(go.Bar(
        name="탐모라 매출(백만)", x=months, y=revenue,
        marker_color=COLORS["teal"], opacity=0.6, marker_line_width=0,
        hovertemplate="%{x}<br>매출: %{y:.1f}백만원<extra></extra>"
    ), secondary_y=False)

    fig.add_trace(go.Scatter(
        name="이용객(명)", x=months, y=pax,
        mode="lines+markers",
        line=dict(color=COLORS["amber"], width=2),
        marker=dict(size=5, color=COLORS["amber"]),
        hovertemplate="%{x}<br>이용객: %{y:,}명<extra></extra>"
    ), secondary_y=True)

    fig.update_layout(
        paper_bgcolor="white",
        plot_bgcolor="white",
        font=dict(family="Noto Sans KR, sans-serif", size=12, color="#333"),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1, font_size=11),
        height=220,
        yaxis=dict(title="백만원", gridcolor="#F5F5F5"),
        yaxis2=dict(title="이용객(명)", gridcolor="rgba(0,0,0,0)"),
        hovermode="x unified",
    )
    return fig

# ─────────────────────────────────────────────
# 사이드바 — 설정 & 데이터 갱신
# ─────────────────────────────────────────────
def render_sidebar():
    with st.sidebar:
        st.markdown("### ⚙️ 설정")
        st.markdown("---")
        if st.button("🔄 데이터 새로고침", use_container_width=True):
            st.cache_data.clear()
            st.rerun()

        st.markdown("---")
        st.markdown("**데이터 연동 정보**")
        st.markdown(f"""
        - 📊 구글 시트 연동
        - ⏱ 5분마다 자동 갱신
        - 🕐 마지막 갱신: {datetime.now().strftime('%H:%M')}
        """)

        st.markdown("---")
        st.markdown("**접속 현황**")
        st.markdown("- 내부 전용 대시보드\n- 호텔사업팀 운영")

        st.markdown("---")
        if st.button("🔒 로그아웃", use_container_width=True):
            st.session_state.authenticated = False
            st.rerun()

# ─────────────────────────────────────────────
# 메인 대시보드
# ─────────────────────────────────────────────
def render_dashboard():
    render_sidebar()

    # ── 헤더 ──────────────────────────────────
    now_str = datetime.now().strftime("%Y년 %m월 %d일 %H:%M 기준")
    st.markdown(f"""
    <div class="main-header">
        <h1>🏨 호텔 더본 제주 — 운영 현황 대시보드</h1>
        <p>내부 전용 | {now_str} | 5분마다 자동 갱신</p>
    </div>
    """, unsafe_allow_html=True)

    # ── 구글 시트 데이터 로드 ─────────────────
    with st.spinner("구글 시트 데이터 불러오는 중..."):
        raw_occ = load_sheet_data(SHEET_ID)

    # 시트 데이터 파싱 시도 → 실패 시 기준 데이터 사용
    df_yearly = pd.DataFrame(BASE_YEARLY)

    # ─────────────────────────────────────────
    # 2026년 실시간 현황 (상단 게이지 + KPI)
    # ─────────────────────────────────────────
    st.markdown("### 📌 2026년 실시간 현황")

    # 2026 데이터 (구글 시트에서 읽어오거나 수동 입력)
    data_2026 = {
        "1월": {"점유율": 84.6, "객실매출": 3.83, "단가": 110379, "탐모라손익": -83.2},
        "2월": {"점유율": 94.0, "객실매출": 4.31, "단가": 122953, "탐모라손익": -76.0},
        "3월": {"점유율": 90.1, "객실매출": 4.85, "단가": None,   "탐모라손익": -53.9},
    }
    latest_month = "3월"
    latest = data_2026[latest_month]

    # KPI 카드 4개
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        kpi_card(
            f"객실 점유율 ({latest_month})",
            f"{latest['점유율']}%",
            "▼ 전년 95.9% 대비 -5.8%p",
            "neg"
        )
    with c2:
        kpi_card(
            f"객실매출 ({latest_month})",
            f"{latest['객실매출']:.2f}억",
            "전년 동월 대비 ±0%",
            "neu"
        )
    with c3:
        yoy_cum = round(((3.83+4.31+4.85)/(5.06+4.34+4.85)-1)*100, 1)
        kpi_card(
            "객실매출 누계 (1~3월)",
            "12.99억",
            f"▼ 전년대비 {yoy_cum}%",
            "neg"
        )
    with c4:
        kpi_card(
            "탐모라 누계 손익 (1~3월)",
            "-2.13억",
            "수도광열비 미포함",
            "neg"
        )

    st.markdown("<br>", unsafe_allow_html=True)

    # ── 게이지 3개 ─────────────────────────────
    g1, g2, g3 = st.columns(3)
    with g1:
        st.plotly_chart(chart_gauge(84.6, "1월 점유율", reference=95.4), use_container_width=True, config={"displayModeBar": False})
    with g2:
        st.plotly_chart(chart_gauge(94.0, "2월 점유율", reference=96.5), use_container_width=True, config={"displayModeBar": False})
    with g3:
        st.plotly_chart(chart_gauge(90.1, "3월 점유율", reference=95.7), use_container_width=True, config={"displayModeBar": False})

    st.caption("🔴 기준선: 전년 동월 점유율 | 초록: 85%+ | 주황: 70~85% | 빨강: 70% 미만")

    st.markdown("---")

    # ─────────────────────────────────────────
    # 2026 실적 vs 목표
    # ─────────────────────────────────────────
    st.markdown("### 📊 2026년 객실매출 실적 vs 목표")
    st.caption("목표: 80% OCC 기준 | 전년 동월 실적 비교 포함")

    monthly_2026 = {
        "1월 (84.6%)": {"실적": 3.83, "목표": 4.07, "전년": 5.06},
        "2월 (94.0%)": {"실적": 4.31, "목표": 4.38, "전년": 4.34},
        "3월 (90.1%)": {"실적": 4.85, "목표": 4.05, "전년": 4.85},
    }
    st.plotly_chart(chart_actual_vs_target(monthly_2026), use_container_width=True, config={"displayModeBar": False})

    # 달성률 테이블
    tbl_data = []
    for m, v in monthly_2026.items():
        rate = round(v["실적"] / v["목표"] * 100, 1)
        yoy  = round((v["실적"] / v["전년"] - 1) * 100, 1)
        tbl_data.append({
            "월": m,
            "실적(억)": f"{v['실적']:.2f}",
            "목표(억)": f"{v['목표']:.2f}",
            "목표달성률": f"{rate}%",
            "전년대비": f"{'▲' if yoy>=0 else '▼'} {abs(yoy)}%",
        })
    st.dataframe(pd.DataFrame(tbl_data), use_container_width=True, hide_index=True)

    st.markdown("---")

    # ─────────────────────────────────────────
    # 연도별 매출 & 순이익 추이
    # ─────────────────────────────────────────
    st.markdown("### 📈 연도별 매출 & 순이익 추이 (2017~2025)")
    st.plotly_chart(chart_yearly_revenue(df_yearly), use_container_width=True, config={"displayModeBar": False})

    st.markdown("---")

    # ─────────────────────────────────────────
    # 점유율 & 평균단가
    # ─────────────────────────────────────────
    col_a, col_b = st.columns([3, 2])

    with col_a:
        st.markdown("### 🛏 연도별 점유율 & 평균단가")
        st.plotly_chart(chart_occ_adr(df_yearly), use_container_width=True, config={"displayModeBar": False})

    with col_b:
        st.markdown("### 📋 연도별 요약")
        summary = pd.DataFrame({
            "연도":   df_yearly["연도"],
            "점유율": [f"{v}%" for v in df_yearly["점유율"]],
            "단가":   [f"₩{int(v*1000):,}" for v in df_yearly["평균단가"]],
            "순이익": [f"{'▲' if v>=0 else '▼'} {abs(v):.1f}억" for v in df_yearly["순이익"]],
        })
        st.dataframe(summary, use_container_width=True, hide_index=True, height=280)

    st.markdown("---")

    # ─────────────────────────────────────────
    # 탐모라 손익
    # ─────────────────────────────────────────
    st.markdown("### 🍽 탐모라 손익 현황")
    st.caption("수도광열비 미포함 | 전략적 Loss Leader — 객실 점유율 앵커 역할")

    t25 = [-74.2,-57.9,-51.8,-48.2,-58.5,-54.7,-56.0,-47.6,-46.9,-53.3,-50.6,-38.8]
    t26 = [-83.2,-76.0,-53.9,None,None,None,None,None,None,None,None,None]

    st.plotly_chart(chart_tambura_pnl(t25, t26), use_container_width=True, config={"displayModeBar": False})

    # 탐모라 KPI
    tc1, tc2, tc3, tc4 = st.columns(4)
    with tc1:
        kpi_card("2025 연간 손실", "-6.38억", "수도광열비 미포함", "neg")
    with tc2:
        kpi_card("2026 YTD 손실", "-2.13억", "1~3월 누계", "neg")
    with tc3:
        kpi_card("2025 연간 이용객", "91,268명", "일평균 250명", "neu")
    with tc4:
        kpi_card("투숙객 조식 단가", "₩12,000", "외부가 별도 적용", "neu")

    st.markdown("<br>", unsafe_allow_html=True)

    t25_rev = [96.7,84.5,87.0,86.7,82.2,73.9,61.4,80.1,78.8,86.6,85.1,90.2]
    t25_pax = [8925,7797,8074,7942,7540,6773,5629,7347,7225,7943,7805,8268]
    st.markdown("#### 탐모라 월별 매출 & 이용객 (2025년)")
    st.plotly_chart(chart_tambura_rev(t25_rev, t25_pax), use_container_width=True, config={"displayModeBar": False})

    st.markdown("---")

    # ─────────────────────────────────────────
    # 인력 현황
    # ─────────────────────────────────────────
    st.markdown("### 👥 인력 현황")

    hc1, hc2, hc3, hc4 = st.columns(4)
    with hc1:
        kpi_card("총 인원", "78명", "호텔 54 + 외주 24", "neu")
    with hc2:
        kpi_card("남 / 여", "27 / 23", "호텔 정직원 기준", "neu")
    with hc3:
        kpi_card("영업 / 경영 / 시설", "37 / 5 / 6", "팀별 배분", "neu")
    with hc4:
        kpi_card("총지배인", "홍영건", "경영지원팀장: 이용준", "neu")

    st.markdown("<br>", unsafe_allow_html=True)

    # 직위별 차트
    positions = ["사원","주임","대리","과장","차장","부장","수석부장"]
    counts    = [16, 13, 11, 4, 1, 2, 1]
    fig_staff = go.Figure(go.Bar(
        x=counts, y=positions,
        orientation="h",
        marker_color=COLORS["blue"],
        marker_opacity=0.65,
        marker_line_width=0,
        text=[f"{c}명" for c in counts],
        textposition="outside",
        hovertemplate="%{y}: %{x}명<extra></extra>"
    ))
    fig_staff.update_layout(
        paper_bgcolor="white",
        plot_bgcolor="white",
        font=dict(family="Noto Sans KR, sans-serif", size=12, color="#333"),
        height=220,
        xaxis=dict(title="인원(명)", gridcolor="#F5F5F5", range=[0, 20]),
        yaxis=dict(gridcolor="rgba(0,0,0,0)"),
        margin=dict(l=10, r=60, t=20, b=10),
    )
    st.plotly_chart(fig_staff, use_container_width=True, config={"displayModeBar": False})

    # ─────────────────────────────────────────
    # 경쟁사 요금 현황 (참고)
    # ─────────────────────────────────────────
    st.markdown("---")
    st.markdown("### 🔍 경쟁사 요금 현황 (2026년 기준)")
    competitors = pd.DataFrame([
        {"호텔": "랜딩관 (서귀포)", "기간": "1~2월", "평일": "₩154,000", "주말": "₩165,000", "비고": "전년대비 +11%"},
        {"호텔": "롯데시티 (제주)", "기간": "1~2월", "평일": "₩143,000", "주말": "-",        "비고": "전년대비 +13%"},
        {"호텔": "볼튼호텔 (제주)", "기간": "7~8월", "평일": "₩215,000", "주말": "₩215,000", "비고": "극성수기 기준"},
        {"호텔": "신라스테이 (제주)", "기간": "5월", "평일": "₩197,780", "주말": "-",        "비고": "연휴 ₩267,960"},
        {"호텔": "부영호텔 (서귀포)", "기간": "3월", "평일": "₩90,000",  "주말": "₩120,000", "비고": "전년대비 -31% (가격 인하)"},
    ])
    st.dataframe(competitors, use_container_width=True, hide_index=True)
    st.caption("출처: 구글 시트 경쟁사 요금 조사 탭 | 호텔 더본 제주 2026년 1~3월 평일 기준: ₩110,000~132,000")

    # ─────────────────────────────────────────
    # 푸터
    # ─────────────────────────────────────────
    st.markdown("---")
    st.markdown("""
    <div style="text-align:center; color:#aaa; font-size:.72rem; padding: .5rem 0 1rem;">
        호텔 더본 제주 — 내부 운영 전용 대시보드 | 호텔사업팀<br>
        데이터 출처: 구글 시트 (2017~2026 점유율·가격·손익 총정리) | 5분 자동 갱신
    </div>
    """, unsafe_allow_html=True)

# ─────────────────────────────────────────────
# 앱 실행 진입점
# ─────────────────────────────────────────────
def main():
    if not check_password():
        return
    render_dashboard()

if __name__ == "__main__":
    main()
