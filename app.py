import streamlit as st
import pandas as pd
import plotly.express as px
from data_loader import load_data
import os

# 페이지 설정
st.set_page_config(page_title="NemoStore 상권 분석 대시보드", layout="wide")

# 데이터 로딩
DB_PATH = os.path.join("data", "nemostore.db")
try:
    df_raw = load_data(DB_PATH)
except Exception as e:
    st.error(f"데이터를 불러오는 중 오류가 발생했습니다: {e}")
    st.stop()

# 사이드바 필터
st.sidebar.header("🔍 검색 필터")

# 업종 필터 (멀티셀렉트)
all_biz = sorted(df_raw['businessMiddleCodeName'].unique())
selected_biz = st.sidebar.multiselect("업종 선택", all_biz, default=[])

# 가격 타입 필터 (라디오버튼)
price_types = sorted(df_raw['priceTypeName'].unique())
selected_price_type = st.sidebar.radio("가격 타입", price_types)

# 월세 범위 필터 (슬라이더)
max_rent = int(df_raw['monthlyRent'].max())
selected_rent = st.sidebar.slider("월세 범위 (만원)", 0, max_rent, (0, max_rent))

# 데이터 필터링 적용
df = df_raw.copy()
if selected_biz:
    df = df[df['businessMiddleCodeName'].isin(selected_biz)]
df = df[df['priceTypeName'] == selected_price_type]
df = df[(df['monthlyRent'] >= selected_rent[0]) & (df['monthlyRent'] <= selected_rent[1])]

# 탭 구성
tab1, tab2, tab3 = st.tabs(["📁 상권 개요", "📁 가격 분석", "📁 매물 탐색"])

# --- 탭 1: 상권 개요 ---
with tab1:
    st.header("📍 상권 전체 현황")
    
    # KPI 카드
    if not df.empty:
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("총 매물 수", f"{len(df):,}개")
        col2.metric("평균 월세", f"{df['monthlyRent'].mean():.0f}만원")
        col3.metric("평균 보증금", f"{df['deposit'].mean():.0f}만원")
        
        # 임대/매매 비율 계산을 위해 전체(필터링 전) 또는 특정 기준 사용 가능하나 
        # 여기서는 필터링된 데이터 안에서의 현황보다는 전체 비율을 보여주거나 
        # 필터링 조건 내에서의 비중을 보여줌
        rent_count = len(df[df['priceTypeName'] == '임대'])
        sale_count = len(df[df['priceTypeName'] == '매매'])
        total = max(1, len(df))
        col4.metric("임대 비중", f"{(rent_count/total)*100:.1f}%")

    st.divider()
    
    c1, c2 = st.columns(2)
    
    with c1:
        st.subheader("🏢 업종별 매물 빈도 (상위 10)")
        top_biz = df['businessMiddleCodeName'].value_counts().head(10).reset_index()
        top_biz.columns = ['업종', '매물수']
        fig_biz = px.bar(top_biz, x='업종', y='매물수', color='업종', text='매물수')
        st.plotly_chart(fig_biz, use_container_width=True)
        
    with c2:
        st.subheader("🚇 역세권별 매물 분포")
        station_stats = df.groupby('station_name').agg({'id':'count', 'monthlyRent':'mean'}).reset_index()
        station_stats.columns = ['역이름', '매물수', '평균월세']
        station_stats = station_stats.sort_values('매물수', ascending=False).head(10)
        fig_st = px.bar(station_stats, x='역이름', y='매물수', color='평균월세', 
                        labels={'매물수':'매물 수(개)', '평균월세':'평균 월세(만원)'},
                        title="Top 10 역세권 매물 수 및 평균 월세")
        st.plotly_chart(fig_st, use_container_width=True)

    st.subheader("💰 가격 타입 비중")
    fig_price = px.pie(df, names='priceTypeName', hole=0.4, title="임대 vs 매매 비중")
    st.plotly_chart(fig_price, use_container_width=True)

# --- 탭 2: 가격 분석 ---
with tab2:
    st.header("📊 가격 상세 분석")
    
    # 추가 필터 (탭 2 전용)
    c_f1, c_f2 = st.columns(2)
    with c_f1:
        size_range = st.slider("면적 범위 (㎡)", 0, int(df_raw['size'].max()), (0, int(df_raw['size'].max())))
    with c_f2:
        floors = st.multiselect("층수 선택", ["지하", "1층", "2층 이상"], default=["지하", "1층", "2층 이상"])
    
    df_ana = df[(df['size'] >= size_range[0]) & (df['size'] <= size_range[1]) & (df['floor_cat'].isin(floors))]
    
    remove_outliers = st.toggle("이상치 제거 (상위 5% 제외)", value=False)
    if remove_outliers and not df_ana.empty:
        q_rent = df_ana['monthlyRent'].quantile(0.95)
        df_ana = df_ana[df_ana['monthlyRent'] <= q_rent]

    st.divider()

    c1, c2 = st.columns(2)
    with c1:
        st.subheader("💵 보증금/월세 분포")
        price_col = st.selectbox("항목 선택", ["monthlyRent", "deposit"])
        fig_hist = px.histogram(df_ana, x=price_col, nbins=30, marginal="box", 
                                title=f"{price_col} 분포", labels={price_col: '금액(만원)'})
        st.plotly_chart(fig_hist, use_container_width=True)
        
    with c2:
        st.subheader("🏢 층수별 월세 분석")
        fig_box = px.box(df_ana, x="floor_cat", y="monthlyRent", color="floor_cat",
                         points="all", title="층수별 월세 박스플롯")
        st.plotly_chart(fig_box, use_container_width=True)

    st.divider()
    
    st.subheader("🏢 층별 평균 월세 규모")
    floor_avg = df_ana.groupby('floor_cat')['monthlyRent'].mean().reset_index()
    floor_avg.columns = ['층구분', '평균월세(만원)']
    fig_floor_bar = px.bar(floor_avg, x='층구분', y='평균월세(만원)', color='층구분', text_auto='.0f',
                          title="층구분별 평균 월세 비교")
    st.plotly_chart(fig_floor_bar, use_container_width=True)

    st.divider()

    c3, c4 = st.columns(2)
    with c3:
        st.subheader("📐 면적 vs 월세")
        fig_scat = px.scatter(df_ana, x="size", y="monthlyRent", color="businessMiddleCodeName",
                             hover_data=["title", "areaPrice"], size_max=15,
                             labels={"size":"면적(㎡)", "monthlyRent":"월세(만원)"},
                             title="면적 대비 월세 (업종별 색상)")
        st.plotly_chart(fig_scat, use_container_width=True)
        
    with c4:
        st.subheader("📈 월세 vs 관리비 상관관계")
        fig_reg = px.scatter(df_ana, x="monthlyRent", y="maintenanceFee", trendline="ols",
                             labels={"monthlyRent":"월세(만원)", "maintenanceFee":"관리비(만원)"},
                             title="월세 vs 관리비 (추세선 포함)")
        st.plotly_chart(fig_reg, use_container_width=True)

# --- 탭 3: 매물 탐색 ---
with tab3:
    st.header("🔍 매물 탐색")
    
    # 상세 필터링
    c_s1, c_s2, c_s3 = st.columns(3)
    with c_s1:
        stations = ["전체"] + sorted(df_raw['station_name'].unique().tolist())
        sel_station = st.selectbox("역세권 선택", stations)
    with c_s2:
        sort_opt = st.selectbox("정렬 기준", ["월세 낮은 순", "월세 높은 순", "면적 큰 순", "조회수 높은 순"])
    with c_s3:
        price_col_search = st.multiselect("보여줄 가격 정보", ["보증금", "월세", "관리비", "권리금"], default=["보증금", "월세"])

    # 필터링 적용 (탭 3용)
    df_exp = df.copy()
    if sel_station != "전체":
        df_exp = df_exp[df_exp['station_name'] == sel_station]
        
    # 정렬
    if sort_opt == "월세 낮은 순":
        df_exp = df_exp.sort_values("monthlyRent")
    elif sort_opt == "월세 높은 순":
        df_exp = df_exp.sort_values("monthlyRent", ascending=False)
    elif sort_opt == "면적 큰 순":
        df_exp = df_exp.sort_values("size", ascending=False)
    elif sort_opt == "조회수 높은 순":
        df_exp = df_exp.sort_values("viewCount", ascending=False)

    st.markdown(f"**검색 결과: {len(df_exp):,}건**")
    
    # 데이터프레임 표시 (컬럼명 한글화)
    column_mapping = {
        'title': '매물명',
        'businessMiddleCodeName': '업종',
        'station_name': '역세권',
        'floor_cat': '층구분',
        'size': '면적(㎡)',
        'monthlyRent': '월세(만원)',
        'deposit': '보증금(만원)',
        'maintenanceFee': '관리비(만원)'
    }
    
    df_disp = df_exp[list(column_mapping.keys())].rename(columns=column_mapping)
    st.dataframe(df_disp, use_container_width=True)

    st.divider()

    # --- 상대적 가치 평가 (Benchmarking) ---
    st.subheader("⚖️ 매물 상대적 가치 평가 (Benchmarking)")
    if not df_exp.empty:
        target_title = st.selectbox("평가할 매물을 선택하세요", df_exp['title'].unique())
        target_item = df_exp[df_exp['title'] == target_title].iloc[0]
        
        # 기준 데이터 계산
        area_avg = df_raw[df_raw['station_name'] == target_item['station_name']]['monthlyRent'].mean()
        biz_avg = df_raw[df_raw['businessMiddleCodeName'] == target_item['businessMiddleCodeName']]['monthlyRent'].mean()
        
        c1, c2, c3 = st.columns(3)
        with c1:
            st.metric("선택 매물 월세", f"{target_item['monthlyRent']:.0f}만원")
        with c2:
            diff_area = ((target_item['monthlyRent'] - area_avg) / area_avg * 100) if area_avg > 0 else 0
            st.metric("지역 평균 대비", f"{area_avg:.0f}만원", f"{diff_area:+.1f}%")
        with c3:
            diff_biz = ((target_item['monthlyRent'] - biz_avg) / biz_avg * 100) if biz_avg > 0 else 0
            st.metric("동일 업종 평균 대비", f"{biz_avg:.0f}만원", f"{diff_biz:+.1f}%")
        
        st.caption(f"💡 이 매물은 동일 지역 평균 대비 {abs(diff_area):.1f}% {'저렴' if diff_area < 0 else '비싼'} 편입니다.")
    
    st.divider()
    
    # 매물 카드 그리드 (3열)
    st.subheader("📋 매물 카드")
    
    # 카드 표시 개수 제한 
    card_limit = 21
    cards = df_exp.head(card_limit)
    
    for i in range(0, len(cards), 3):
        cols = st.columns(3)
        for j in range(3):
            if i + j < len(cards):
                card = cards.iloc[i + j]
                with cols[j]:
                    with st.container(border=True):
                        # 이미지
                        img_url = card['previewPhotoUrl'] if card['previewPhotoUrl'] else "https://via.placeholder.com/300x200?text=No+Image"
                        st.image(img_url, use_container_width=True)
                        # 제목 (짧게)
                        st.markdown(f"**{card['title'][:20]}...**" if len(card['title']) > 20 else f"**{card['title']}**")
                        # 정보
                        st.caption(f"📍 {card['station_name']} | 📏 {card['size']:.1f}㎡")
                        st.write(f"💰 **월세 {card['monthlyRent']:.0f} / 보증 {card['deposit']:.0f}**")
                        st.write(f"🏢 {card['businessMiddleCodeName']} | {card['floor_cat']}")

st.sidebar.markdown("---")
st.sidebar.caption("NemoStore Dashboard v1.0")
