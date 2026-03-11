import sqlite3
import pandas as pd
import streamlit as st
import re

@st.cache_data
def load_data(db_path):
    conn = sqlite3.connect(db_path)
    df = pd.read_sql_query("SELECT * FROM items", conn)
    conn.close()
    
    # 층수 전처리 (floor 레이블링)
    # -1, -2 -> 지하 / 1 -> 1층 / 2~ -> 2층 이상
    def categorize_floor(f):
        try:
            f = int(f)
            if f < 0: return "지하"
            elif f == 1: return "1층"
            else: return "2층 이상"
        except (ValueError, TypeError):
            return "기타"
    
    df['floor_cat'] = df['floor'].apply(categorize_floor)
    
    # 역세권 파싱 (nearSubwayStation에서 역명 추출)
    # 예: "을지로입구역, 도보 7분" -> "을지로입구역"
    def extract_station(s):
        if not s: return "정보없음"
        match = re.search(r'([가-힣|a-zA-Z|0-9]+역)', s)
        return match.group(1) if match else "정보없음"
    
    df['station_name'] = df['nearSubwayStation'].apply(extract_station)
    
    # 숫자형 컬럼 변환 및 결측치 처리
    num_cols = ['deposit', 'monthlyRent', 'premium', 'maintenanceFee', 'size', 'viewCount', 'areaPrice']
    for col in num_cols:
        df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
        
    return df
