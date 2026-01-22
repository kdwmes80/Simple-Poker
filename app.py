import streamlit as st
import eval7
import pandas as pd

# 모바일 화면 최적화 설정
st.set_page_config(page_title="Poker Tournament Analyzer", layout="centered")

# --- 스타일링: 버튼 크기 및 색상 강조 ---
st.markdown("""
    <style>
    div.stButton > button:first-child { width: 100%; height: 60px; font-size: 20px; font-weight: bold; background-color: #007bff; color: white; }
    .stSelectbox label, .stRadio label { font-size: 16px; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

# --- 승률 계산 함수 (eval7) ---
def get_equity(hero, board):
    try:
        hero_cards = [eval7.Card(c) for c in hero]
        board_cards = [eval7.Card(c) for c in board if c]
        
        win_count = 0
        iters = 2000 # 모바일 응답 속도를 고려한 횟수
        
        for _ in range(iters):
            deck = eval7.Deck()
            for c in hero_cards + board_cards:
                if c in deck.cards: deck.cards.remove(c)
            deck.shuffle()
            
            opp_cards = deck.deal(2)
            full_board = board_cards + deck.deal(5 - len(board_cards))
            
            h_score = eval7.evaluate(hero_cards + full_board)
            o_score = eval7.evaluate(opp_cards + full_board)
            
            if h_score > o_score: win_count += 1
            elif h_score == o_score: win_count += 0.5
        return (win_count / iters) * 100
    except:
        return 0

# --- 세션 상태 초기화 (로그 기록용) ---
if 'history' not in st.session_state:
    st.session_state.history = []

# --- 메인 UI ---
st.title("🏆 Poker Pro Mobile")

# [1단계] 초기 설정 및 ICM (사이드바)
with st.sidebar:
    st.header("토너먼트 정보")
    st.session_state.total_players = st.number_input("남은 인원", 2, 100, 9)
    st.session_state.my_bb = st.number_input("내 칩 (BB)", 1.0, 1000.0, 50.0)
    icm_active = st.toggle("ICM 모드 활성화")
    st.divider()
    if st.button("세션 초기화 (Reset)"):
        st.session_state.history = []
        st.rerun()

# [2단계] 카드 입력 (모바일 스크롤 최소화)
st.subheader("내 핸드 (Hero)")
ranks = ['A', 'K', 'Q', 'J', 'T', '9', '8', '7', '6', '5', '4', '3', '2']
suits = {'♠': 's', '♥': 'h', '◆': 'd', '♣': 'c'}

c1, c2 = st.columns(2)
with c1:
    h1 = st.selectbox("Rank 1", ranks) + suits[st.selectbox("Suit 1", list(suits.keys()))]
with c2:
    h2 = st.selectbox("Rank 2", ranks) + suits[st.selectbox("Suit 2", list(suits.keys()))]

st.subheader("공통 카드 (Board)")
b_input = st.text_input("플랍/턴/리버 입력 (예: As Kd Qh 2s)", placeholder="As Kd Qh")
board = b_input.split()

# [3단계] 상대 액션 및 포지션
st.divider()
st.subheader("상대방 액션")
col_pos, col_act = st.columns([1, 1])
with col_pos:
    position = st.radio("포지션", ["IP (유리)", "OOP (불리)"])
with col_act:
    action = st.select_slider("강도", options=["Check", "Call", "Bet", "Raise", "All-in"])

# [4단계] 분석 실행
if st.button("실시간 분석"):
    equity = get_equity([h1, h2], board)
    
    # ICM 보정 (간이 로직: 인원이 적을수록 필요한 승률을 높임)
    risk_premium = (10 - st.session_state.total_players) * 1.5 if icm_active and st.session_state.total_players < 10 else 0
    final_equity = equity - risk_premium
    
    # 결과 표시
    st.metric("최종 승률 (Equity)", f"{final_equity:.1f}%", delta=f"-{risk_premium:.1f}% ICM" if icm_active else None)
    
    if final_equity > 60:
        st.success("🔥 강력 추천: 적극적인 베팅/콜")
    elif final_equity > 45:
        st.warning("⚖️ 마진 핸드: 포지션과 팟 오즈 계산 필요")
    else:
        st.error("🚫 위험: 폴드 권장")
    
    # 로그 추가
    st.session_state.history.append(f"Hero: {h1}{h2} | Board: {b_input} | Action: {action} | Equity: {final_equity:.1f}%")

# [5단계] 히스토리 (Villain 명명)
if st.session_state.history:
    st.divider()
    st.subheader("📜 핸드 히스토리")
    for i, log in enumerate(reversed(st.session_state.history)):
        st.text(f"Hand #{len(st.session_state.history)-i}: {log}")
