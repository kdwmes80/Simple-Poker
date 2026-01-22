import streamlit as st
import eval7

# 페이지 설정
st.set_page_config(page_title="Poker Table Analyzer", layout="centered")

# --- CSS: 포커 테이블 느낌의 커스텀 UI ---
st.markdown("""
    <style>
    .main { background-color: #0e1117; }
    .stButton>button { width: 100%; border-radius: 10px; font-weight: bold; height: 3.5em; }
    .poker-card { border: 2px solid #fff; border-radius: 8px; padding: 10px; text-align: center; font-size: 20px; background: #222; margin: 5px; }
    .hero-pos { color: #00ff00; font-size: 14px; font-weight: bold; text-align: center; }
    .villain-box { padding: 5px; border-radius: 5px; text-align: center; background: #1a1c24; border: 1px solid #333; }
    .folded { opacity: 0.3; background: #000; color: #555; }
    </style>
    """, unsafe_allow_html=True)

# --- 세션 상태 초기화 ---
if 'step' not in st.session_state: st.session_state.step = 1 # 1: 인원설정, 2: 분석
if 'folded' not in st.session_state: st.session_state.folded = []
if 'dealer' not in st.session_state: st.session_state.dealer = 0
if 'hero_hand' not in st.session_state: st.session_state.hero_hand = []
if 'board' not in st.session_state: st.session_state.board = []
if 'game_stage' not in st.session_state: st.session_state.game_stage = "Pre-flop"

# --- 1단계: 인원 및 기본 모드 설정 ---
if st.session_state.step == 1:
    st.title("🏟️ Table Setup")
    total = st.slider("테이블 인원 선택", 2, 10, 9)
    
    col1, col2 = st.columns(2)
    with col1: icm = st.toggle("🏆 ICM 분석 모드")
    with col2: pushfold = st.toggle("⚔️ Push/Fold 모드")
    
    if st.button("게임 시작"):
        st.session_state.total_players = total
        st.session_state.icm = icm
        st.session_state.pushfold = pushfold
        st.session_state.step = 2
        st.rerun()

# --- 2단계: 메인 분석 세션 ---
else:
    # 상단 정보바
    st.caption(f"Stage: {st.session_state.game_stage} | Players: {st.session_state.total_players}")
    
    # 2-2 & 2-3: 빌런 테이블 레이아웃 (포커 테이블 형상)
    st.write("### Table Layout")
    cols = st.columns(st.session_state.total_players - 1)
    for i in range(st.session_state.total_players - 1):
        v_idx = i + 1
        is_folded = v_idx in st.session_state.folded
        is_dealer = st.session_state.dealer == v_idx
        
        with cols[i]:
            style = "folded" if is_folded else ""
            st.markdown(f"<div class='villain-box {style}'>V{v_idx}</div>", unsafe_allow_html=True)
            if st.button("F", key=f"f{v_idx}", help="Fold"):
                if v_idx in st.session_state.folded: st.session_state.folded.remove(v_idx)
                else: st.session_state.folded.append(v_idx)
                st.rerun()
            if st.button("D", key=f"d{v_idx}", help="Dealer"):
                st.session_state.dealer = v_idx
                st.rerun()

    st.divider()

    # 2-1: Hero 핸드 입력 (터치 방식)
    st.subheader("My Hand")
    ranks = ['A','K','Q','J','T','9','8','7','6','5','4','3','2']
    suits = {'♠':'s','♥':'h','◆':'d','♣':'c'}
    
    h_col1, h_col2 = st.columns(2)
    with h_col1:
        r1 = st.selectbox("Rank 1", ranks, key="r1")
        s1 = st.selectbox("Suit 1", list(suits.keys()), key="s1")
    with h_col2:
        r2 = st.selectbox("Rank 2", ranks, key="r2")
        s2 = st.selectbox("Suit 2", list(suits.keys()), key="s2")
    
    # 포지션 자동 계산 (단순화: 딜러 위치 기준)
    pos_label = "IP (Button)" if st.session_state.dealer == 0 else "OOP"
    st.markdown(f"<div class='hero-pos'>Position: {pos_label}</div>", unsafe_allow_html=True)

    st.divider()

    # 2-4: 단계별 보드 입력 및 분석
    st.subheader(f"Board: {st.session_state.game_stage}")
    
    if st.session_state.game_stage != "Pre-flop":
        b_cols = st.columns(5)
        # 플랍 3장, 턴 1장, 리버 1장 순차적 입력 로직 필요 (여기선 통합 입력)
        board_input = st.text_input("보드 카드 입력 (예: As Kd Qh)", key="board_input")
        st.session_state.board = board_input.split()

    # 상대 액션
    action = st.select_slider("상대 액션", options=["Check", "Call", "Bet", "Raise", "All-in"])

    if st.button("🔍 OK - 분석 실행"):
        # 여기에 eval7 분석 엔진 연동 (기존 로직)
        st.metric("승률 (Equity)", "65.4%")
        st.metric("아우츠/메이드률", "18.5%")
        
        # 단계 전환 버튼 노출
        stages = ["Pre-flop", "Flop", "Turn", "River", "Result"]
        current_idx = stages.index(st.session_state.game_stage)
        if current_idx < 4:
            if st.button("다음 단계로"):
                st.session_state.game_stage = stages[current_idx + 1]
                st.rerun()

    # 초기화 버튼
    if st.button("🔄 세션 초기화"):
        st.session_state.step = 1
        st.session_state.folded = []
        st.session_state.board = []
        st.session_state.game_stage = "Pre-flop"
        st.rerun()
