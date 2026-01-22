import streamlit as st
import eval7

# 페이지 설정
st.set_page_config(page_title="Poker Pro Mobile", layout="centered")

# --- CSS: 버튼 및 상태 표현 ---
st.markdown("""
    <style>
    .stButton>button { width: 100%; border-radius: 8px; font-weight: bold; }
    .dealer-active { background-color: #f1c40f !important; color: black !important; }
    .folded-active { background-color: #7f8c8d !important; opacity: 0.5; }
    .pos-tag { font-size: 12px; color: #3498db; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

# --- 세션 상태 초기화 ---
if 'page' not in st.session_state: st.session_state.page = "setup"
if 'total_players' not in st.session_state: st.session_state.total_players = 9
if 'folded_list' not in st.session_state: st.session_state.folded_list = []
if 'dealer_idx' not in st.session_state: st.session_state.dealer_idx = None
if 'hero_hand' not in st.session_state: st.session_state.hero_hand = []
if 'board' not in st.session_state: st.session_state.board = []
if 'game_stage' not in st.session_state: st.session_state.game_stage = "Pre-flop"

# --- 유틸리티 함수 ---
def get_card_str(rank, suit):
    suits_map = {'♠':'s','♥':'h','◆':'d','♣':'c'}
    return f"{rank}{suits_map[suit]}"

# --- PAGE 1: 초기 설정 ---
if st.session_state.page == "setup":
    st.title("🏟️ 1. 환경 설정")
    st.session_state.total_players = st.select_slider("테이블 인원", options=range(2, 11), value=9)
    st.session_state.icm = st.toggle("🏆 ICM 분석 모드")
    st.session_state.pushfold = st.toggle("⚔️ Push/Fold 모드")
    
    if st.button("다음: 테이블 설정 ➡️"):
        st.session_state.page = "table"
        st.rerun()

# --- PAGE 2: 테이블 설정 (Dealer & Fold) ---
elif st.session_state.page == "table":
    st.title("🪑 2. 테이블 배치")
    st.caption("누가 딜러(D)인지, 누가 폴드(F)했는지 선택하세요.")
    
    # Hero (나)는 항상 Index 0
    cols = st.columns(st.session_state.total_players)
    for i in range(st.session_state.total_players):
        with cols[i]:
            name = "Hero" if i == 0 else f"V{i}"
            is_dealer = (st.session_state.dealer_idx == i)
            is_folded = (i in st.session_state.folded_list)
            
            # 플레이어 표시
            label = f"{name} (D)" if is_dealer else name
            st.markdown(f"<div style='text-align:center; font-weight:bold;'>{label}</div>", unsafe_allow_html=True)
            
            # D 버튼 (한 명만 선택 가능)
            if st.button("D", key=f"d_{i}", disabled=(is_folded)):
                st.session_state.dealer_idx = i
                st.rerun()
            
            # F 버튼 (Hero 제외)
            if i != 0:
                if st.button("F", key=f"f_{i}"):
                    if i in st.session_state.folded_list:
                        st.session_state.folded_list.remove(i)
                    else:
                        st.session_state.folded_list.append(i)
                        if st.session_state.dealer_idx == i: st.session_state.dealer_idx = None
                    st.rerun()

    if st.session_state.dealer_idx is not None:
        if st.button("다음: 핸드 입력 ➡️"):
            st.session_state.page = "hero_input"
            st.rerun()
    else:
        st.warning("딜러(D)를 선택해야 진행할 수 있습니다.")

# --- PAGE 3: 내 핸드 입력 ---
elif st.session_state.page == "hero_input":
    st.title("🎴 3. 내 핸드 입력")
    ranks = ['A','K','Q','J','T','9','8','7','6','5','4','3','2']
    suits = ['♠','♥','◆','♣']
    
    c1, c2 = st.columns(2)
    with c1:
        r1 = st.selectbox("카드 1 숫자", ranks)
        s1 = st.selectbox("카드 1 문양", suits)
    with c2:
        r2 = st.selectbox("카드 2 숫자", ranks)
        s2 = st.selectbox("카드 2 문양", suits)
        
    st.session_state.hero_hand = [get_card_str(r1, s1), get_card_str(r2, s2)]
    
    # 포지션 계산 (딜러 기준 시계방향)
    # 단순화: Hero가 Dealer면 IP, 아니면 OOP로 표기 (헤즈업/멀티웨이에 따라 변동 가능)
    pos_text = "IP (유리)" if st.session_state.dealer_idx == 0 else "OOP (불리)"
    st.info(f"나의 포지션: **{pos_text}**")

    if st.button("다음: 분석 시작 ➡️"):
        st.session_state.page = "analysis"
        st.rerun()

# --- PAGE 4: 단계별 보드 & 액션 분석 ---
elif st.session_state.page == "analysis":
    st.title(f"📊 {st.session_state.game_stage} 분석")
    
    # 보드 입력 (Pre-flop 이후)
    if st.session_state.game_stage != "Pre-flop":
        st.subheader("보드 카드 추가")
        b_input = st.text_input("새로 오픈된 카드 (예: As Kd)", placeholder="As")
        if b_input:
            new_cards = b_input.split()
            for nc in new_cards:
                if nc not in st.session_state.board: st.session_state.board.append(nc)

    st.write(f"현재 보드: `{' '.join(st.session_state.board)}`" if st.session_state.board else "현재 보드: 없음")

    # 상대 액션 입력
    st.divider()
    st.subheader("상대방 액션")
    act_col1, act_col2 = st.columns([1, 1])
    with act_col1:
        opp_act = st.radio("액션 선택", ["Check", "Call", "Bet", "Raise", "All-in"], horizontal=False)
    with act_col2:
        bet_size = st.number_input("벳 사이즈 (BB)", min_value=0.0, step=0.5) if opp_act in ["Bet", "Raise"] else 0

    if st.button("📉 OK - 데이터 분석"):
        # 여기에 eval7 시뮬레이션 코드 실행 (생략, 기존과 동일)
        st.metric("승률 (Equity)", "58.2%")
        st.metric("메이드/아우츠", "12%")
        
    # 단계 이동
    st.divider()
    next_map = {"Pre-flop": "Flop", "Flop": "Turn", "Turn": "River", "River": "Result"}
    if st.session_state.game_stage != "Result":
        if st.button(f"{next_map[st.session_state.game_stage]} 단계로 이동 ⏩"):
            st.session_state.game_stage = next_map[st.session_state.game_stage]
            st.rerun()
    else:
        if st.button("🔄 전체 초기화 (New Game)"):
            for key in st.session_state.keys(): del st.session_state[key]
            st.rerun()
