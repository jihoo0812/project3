import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# ----------------------------------------------------------------------------
# 기본 설정
# ----------------------------------------------------------------------------
st.set_page_config(
    page_title="LoL 챔피언 스탯 대시보드",
    page_icon="🎮",
    layout="wide",
)

CSV_PATH = "LoL_챔피언.csv"

STAT_COLUMNS = {
    "체력": "체력",
    "체력성장": "체력성장 (레벨당)",
    "마나": "마나",
    "마나성장": "마나성장 (레벨당)",
    "이동속도": "이동속도",
    "방어력": "방어력",
    "마법저항력": "마법저항력",
    "공격사거리": "공격사거리",
    "공격력": "공격력",
    "공격력성장": "공격력성장 (레벨당)",
    "공격속도성장(%)": "공격속도성장(%)",
}

RADAR_STATS = ["체력", "방어력", "마법저항력", "공격력", "공격사거리", "이동속도"]


@st.cache_data
def load_data(path: str) -> pd.DataFrame:
    df = pd.read_csv(path, encoding="utf-8-sig")
    df["역할2"] = df["역할2"].fillna("없음")
    return df


def normalize_for_radar(df: pd.DataFrame, cols: list[str]) -> pd.DataFrame:
    """레이더 차트 표현을 위해 0~100 스케일로 정규화"""
    norm = df.copy()
    for c in cols:
        min_v, max_v = df[c].min(), df[c].max()
        if max_v - min_v == 0:
            norm[c] = 50
        else:
            norm[c] = (df[c] - min_v) / (max_v - min_v) * 100
    return norm


def main():
    df = load_data(CSV_PATH)

    st.title("🎮 리그 오브 레전드 챔피언 스탯 대시보드")
    st.caption(f"총 {len(df)}명의 챔피언 데이터를 담고 있습니다.")

    # ------------------------------------------------------------------
    # 사이드바 필터
    # ------------------------------------------------------------------
    st.sidebar.header("🔍 필터")

    search = st.sidebar.text_input("챔피언 이름 검색 (한글/영문)")

    roles = sorted(df["역할1"].unique())
    selected_roles = st.sidebar.multiselect("역할 (역할1 기준)", roles, default=roles)

    hp_range = st.sidebar.slider(
        "체력 범위",
        int(df["체력"].min()), int(df["체력"].max()),
        (int(df["체력"].min()), int(df["체력"].max())),
    )

    atk_range = st.sidebar.slider(
        "공격력 범위",
        int(df["공격력"].min()), int(df["공격력"].max()),
        (int(df["공격력"].min()), int(df["공격력"].max())),
    )

    filtered = df[
        df["역할1"].isin(selected_roles)
        & df["체력"].between(*hp_range)
        & df["공격력"].between(*atk_range)
    ]

    if search:
        mask = (
            filtered["챔피언"].str.contains(search, case=False, na=False)
            | filtered["영문이름"].str.contains(search, case=False, na=False)
        )
        filtered = filtered[mask]

    st.sidebar.markdown(f"**필터링된 챔피언 수: {len(filtered)}**")

    # ------------------------------------------------------------------
    # 탭 구성
    # ------------------------------------------------------------------
    tab1, tab2, tab3 = st.tabs(["📋 챔피언 목록", "📊 스탯 분포", "🕸️ 챔피언 비교"])

    # -------------------- 탭 1: 목록 --------------------
    with tab1:
        st.subheader("챔피언 목록")
        st.dataframe(
            filtered.rename(columns=STAT_COLUMNS).reset_index(drop=True),
            use_container_width=True,
            height=500,
        )

        col1, col2, col3 = st.columns(3)
        col1.metric("평균 체력", f"{filtered['체력'].mean():.0f}")
        col2.metric("평균 공격력", f"{filtered['공격력'].mean():.1f}")
        col3.metric("평균 이동속도", f"{filtered['이동속도'].mean():.0f}")

    # -------------------- 탭 2: 분포 --------------------
    with tab2:
        st.subheader("스탯 분포 살펴보기")

        c1, c2 = st.columns(2)
        with c1:
            stat_choice = st.selectbox("분포를 볼 스탯 선택", list(STAT_COLUMNS.keys()))
        with c2:
            role_count = df["역할1"].value_counts().reset_index()
            role_count.columns = ["역할", "챔피언 수"]

        fig_hist = px.histogram(
            filtered, x=stat_choice, color="역할1",
            nbins=20, title=f"{STAT_COLUMNS[stat_choice]} 분포",
        )
        st.plotly_chart(fig_hist, use_container_width=True)

        fig_role = px.bar(
            role_count, x="역할", y="챔피언 수",
            title="역할별 챔피언 수 (역할1 기준)", color="역할",
        )
        st.plotly_chart(fig_role, use_container_width=True)

        fig_scatter = px.scatter(
            filtered, x="공격력", y="체력", color="역할1",
            hover_name="챔피언", size="방어력",
            title="공격력 vs 체력 (버블 크기 = 방어력)",
        )
        st.plotly_chart(fig_scatter, use_container_width=True)

    # -------------------- 탭 3: 비교 --------------------
    with tab3:
        st.subheader("챔피언 능력치 비교 (레이더 차트)")

        champ_options = df["챔피언"].tolist()
        selected_champs = st.multiselect(
            "비교할 챔피언 선택 (최대 5명)",
            champ_options,
            default=champ_options[:2] if len(champ_options) >= 2 else champ_options,
            max_selections=5,
        )

        if selected_champs:
            norm_df = normalize_for_radar(df, RADAR_STATS)
            fig = go.Figure()

            for champ in selected_champs:
                row = norm_df[norm_df["챔피언"] == champ]
                raw_row = df[df["챔피언"] == champ]
                values = row[RADAR_STATS].values.flatten().tolist()
                values.append(values[0])
                fig.add_trace(go.Scatterpolar(
                    r=values,
                    theta=RADAR_STATS + [RADAR_STATS[0]],
                    fill="toself",
                    name=champ,
                    hovertext=[
                        f"{stat}: {raw_row[stat].values[0]}" for stat in RADAR_STATS
                    ] + [f"{RADAR_STATS[0]}: {raw_row[RADAR_STATS[0]].values[0]}"],
                ))

            fig.update_layout(
                polar=dict(radialaxis=dict(visible=True, range=[0, 100])),
                showlegend=True,
                title="선택 챔피언 능력치 비교 (0~100 정규화 값)",
            )
            st.plotly_chart(fig, use_container_width=True)

            st.markdown("#### 원본 스탯 값")
            st.dataframe(
                df[df["챔피언"].isin(selected_champs)]
                .set_index("챔피언")[RADAR_STATS]
                .T,
                use_container_width=True,
            )
        else:
            st.info("비교할 챔피언을 1명 이상 선택해주세요.")


if __name__ == "__main__":
    main()
