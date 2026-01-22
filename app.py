import streamlit as st
import eval7

# [기능 보완] 아우츠 계산 함수
def calculate_outs(hero, board):
    if len(board) >= 5: return 0
    hero_c = [eval7.Card(c) for c in hero]
    board_c = [eval7.Card(c) for c in board]
    current_score = eval7.evaluate(hero_c + board_c)
    deck = eval7.Deck()
    for c in hero_c + board_c: deck.cards.remove(c)
    
    outs = 0
    for card in deck.cards:
        if eval7.evaluate(hero_c + board_c + [card]) > current_score:
            outs += 1
    return outs

# --- UI 설정 ---
st.set_page_config(page_title="Poker Pro Master", layout="centered")

st.markdown("""
    <style>
    .stButton>button { width: 100%; border-radius: 12px; height: 3em; font-weight: bold; }
    .folded-unit { opacity: 0.3; filter: grayscale(100%); pointer-events: none; }
    .dealer-label { color: #f1c40f; font-weight: bold; font-size: 12px; }
    .pos-info { background: #1e1e1e; padding: 10px; border-radius: 10px; border-left: 5px solid #3498db; }
    </style>
    """, unsafe_allow_html=True)

# 세션 관리
if 'step' not in st.session_state: st.session_state.step = 1
if 'folded' not in st.session_state: st.session_state.folded = []
if 'dealer' not in st.session_state: st.session_state.dealer = None
if 'hero_hand' not in st.session_state: st.session_state.hero_hand = []
if 'board' not in st.session_state: st.session_state.board = []
if 'stage' not in st.session_state: st.session_state.stage = "Pre-flop"

# --- STEP 1: 설정 ---
if st.session_state.step == 1:
    st.title("🏟️ Step 1. Setup")
    count = st.select_slider("플레이어 수", options=range(2, 11), value=9)
    c1, c2 = st.columns(2)
    with c1: icm = st.toggle("🏆 ICM 분석")
    with c2: pf = st.toggle("⚔️ Push/Fold")
    if st.button("테이블 입장 ➡️"):
        st.session_state.total = count
        st.session_state.step = 2
        st.rerun()

# --- STEP 2: 테이블 (D/F 설정) ---
elif st.session_state.step == 2:
    st.title("🪑 Step 2. Table")
    st.caption("F를 누르면 해당 플레이어는 이번 세션에서 완전히 제외(회색)됩니다.")
    
    cols = st.columns(3)
    for i in range(st.session_state.total):
        with cols[i % 3]:
            is_f = i in st.session_state.folded
            is_d = st.session_state.dealer == i
            
            # 비활성화 컨테이너
            st.markdown(f"<div class='{'folded-unit' if is_f else ''}'>", unsafe_allow_html=True)
            st.write(f"**{'Hero' if i==0 else f'V{i}'}**")
            if is_d: st.markdown("<span class='dealer-label'>[DEALER]</span>", unsafe_allow_html=True)
            
            # D 버튼: 누군가 선택되면 다른 사람들은 비활성화
            d_btn_disabled = is_f or (st.session_state.dealer is not None and st.session_state.dealer != i)
            if st.button(f"D", key=f"d{i}", disabled=d_btn_disabled):
                st.session_state.dealer = None if is_d else i
                st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)
            
            # F 버튼 (Hero 제외)
            if i != 0:
                if st.button("Fold" if not is_f else "Unfold", key=f"f{i}"):
                    if is_f: st.session_state.folded.remove(i)
                    else: 
                        st.session_state.folded.append(i)
                        if is_d: st.session_state.dealer = None
                    st.rerun()

    if st.session_state.dealer is not None:
        if st.button("핸드 입력으로 이동 ➡️"): st.session_state.step = 3; st.rerun()

# --- STEP 3: 핸드 입력 ---
elif st.session_state.step == 3:
    st.title("🎴 Step 3. My Hand")
    ranks = ['A','K','Q','J','T','9','8','7','6','5','4','3','2']
    suits = {'♠':'s','♥':'h','◆':'d','♣':'c'}
    
    c1, c2 = st.columns(2)
    with c1:
        r1 = st.selectbox("첫 번째 숫자", ranks)
        s1 = st.selectbox("첫 번째 문양", list(suits.keys()))
    with c2:
        r2 = st.selectbox("두 번째 숫자", ranks)
        s2 = st.selectbox("두 번째 문양", list(suits.keys()))
    
    st.session_state.hero_hand = [f"{r1}{suits[s1]}", f"{r2}{suits[s2]}"]
    
    # 포지션 자동 계산 알림
    pos = "IP" if st.session_state.dealer == 0 else "OOP"
    st.markdown(f"<div class='pos-info'>나의 포지션: <b>{pos}</b></div>", unsafe_allow_html=True)
    
    if st.button("분석 세션 시작 ➡️"): st.session_state.step = 4; st.rerun()

# --- STEP 4: 분석 (액션 버튼화 및 단계별 진행) ---
elif st.session_state.step == 4:
    st.title(f"📊 {st.session_state.stage}")
    
    # 1. 보드 카드 입력 (단계별)
    if st.session_state.stage != "Pre-flop":
        b_in = st.text_input("새 카드 입력 (예: As)", key="b_in").split()
        for card in b_in:
            if card not in st.session_state.board: st.session_state.board.append(card)
    
    st.write(f"**현재 보드:** {' '.join(st.session_state.board) if st.session_state.board else '없음'}")

    # 2. 상대 액션 (버튼형)
    st.subheader("상대 액션 선택")
    act_cols = st.columns(5)
    actions = ["Check", "Call", "Bet", "Raise", "All-in"]
    selected_act = None
    for idx, act in enumerate(actions):
        if act_cols[idx].button(act):
            st.session_state.last_action = act

    if 'last_action' in st.session_state:
        st.info(f"선택된 액션: {st.session_state.last_action}")
        if st.session_state.last_action in ["Bet", "Raise"]:
            size = st.number_input("벳 사이즈 (BB)", min_value=0.0, value=2.0)
        
        if st.button("🧮 승률 계산 실행"):
            # eval7 엔진 가동
            equity = 62.4 # 예시값
            outs = calculate_outs(st.session_state.hero_hand, st.session_state.board)
            st.metric("승률 (Equity)", f"{equity}%")
            st.metric("아우츠 (Outs)", f"{outs}개")

    # 3. 단계 이동
    st.divider()
    nav_cols = st.columns(2)
    next_stages = {"Pre-flop":"Flop", "Flop":"Turn", "Turn":"River", "River":"End"}
    if nav_cols[0].button("전 단계로"):
        st.session_state.step = 2; st.rerun()
    if nav_cols[1].button("다음 단계로"):
        st.session_state.stage = next_stages[st.session_state.stage]
        st.rerun()
