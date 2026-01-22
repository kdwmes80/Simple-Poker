import streamlit as st
import eval7

# --- 핵심 로직: 승률 및 아우츠 계산 ---
def calculate_poker_stats(hero_hand, board):
    try:
        hero_c = [eval7.Card(c) for c in hero_hand]
        board_c = [eval7.Card(c) for c in board]
        
        win_count = 0
        iters = 1000 # 모바일 속도를 위해 1000회 세팅
        for _ in range(iters):
            deck = eval7.Deck()
            for c in hero_c + board_c:
                if c in deck.cards: deck.cards.remove(c)
            deck.shuffle()
            
            opp_cards = deck.deal(2)
            temp_board = board_c + deck.deal(5 - len(board_c))
            
            h_s = eval7.evaluate(hero_c + temp_board)
            o_s = eval7.evaluate(opp_cards + temp_board)
            if h_s > o_s: win_count += 1
            elif h_s == o_s: win_count += 0.5
            
        equity = (win_count / iters) * 100
        outs = 0
        if len(board_c) < 5:
            current_score = eval7.evaluate(hero_c + board_c)
            deck = eval7.Deck()
            for c in hero_c + board_c: 
                if c in deck.cards: deck.cards.remove(c)
            for c in deck.cards:
                if eval7.evaluate(hero_c + board_c + [c]) > current_score:
                    outs += 1
        return equity, outs
    except:
        return 0, 0

# --- UI 설정 ---
st.set_page_config(page_title="Poker Pro Master", layout="centered")

st.markdown("""
    <style>
    .stButton>button { width: 100%; border-radius: 8px; height: 3em; font-weight: bold; }
    .folded-unit { opacity: 0.2; filter: grayscale(100%); pointer-events: none; }
    .card-active { background-color: #2e7d32 !important; color: white !important; }
    .advice-box { padding: 15px; border-radius: 10px; margin: 10px 0; font-weight: bold; text-align: center; }
    </style>
    """, unsafe_allow_html=True)

# 세션 상태 초기화
if 'step' not in st.session_state: st.session_state.step = 1
if 'folded' not in st.session_state: st.session_state.folded = []
if 'dealer' not in st.session_state: st.session_state.dealer = None
if 'hero_hand' not in st.session_state: st.session_state.hero_hand = []
if 'board' not in st.session_state: st.session_state.board = []
if 'stage' not in st.session_state: st.session_state.stage = "Pre-flop"

# 모든 카드 리스트 생성 (중복 방지용)
ranks = ['A','K','Q','J','T','9','8','7','6','5','4','3','2']
suits = {'♠':'s','♥':'h','◆':'d','♣':'c'}
all_deck = [f"{r}{s_v}" for r in ranks for s_v in suits.values()]

# --- STEP 1: 설정 ---
if st.session_state.step == 1:
    st.title("🏟️ Step 1. 인원 설정")
    st.session_state.total = st.select_slider("테이블 인원", options=range(2, 11), value=9)
    if st.button("테이블 생성 ➡️"):
        st.session_state.step = 2
        st.rerun()

# --- STEP 2: 테이블 배치 ---
elif st.session_state.step == 2:
    st.title("🪑 Step 2. 테이블 배치")
    cols = st.columns(3)
    for i in range(st.session_state.total):
        with cols[i % 3]:
            is_f = i in st.session_state.folded
            is_d = st.session_state.dealer == i
            st.markdown(f"<div class='{'folded-unit' if is_f else ''}'>", unsafe_allow_html=True)
            st.write(f"**P{i} {'(Hero)' if i==0 else ''}**")
            d_disabled = is_f or (st.session_state.dealer is not None and st.session_state.dealer != i)
            if st.button(f"D", key=f"d{i}", disabled=d_disabled, type="primary" if is_d else "secondary"):
                st.session_state.dealer = i
                st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)
            if i != 0:
                if st.button("Fold" if not is_f else "Unfold", key=f"f{i}"):
                    if is_f: st.session_state.folded.remove(i)
                    else: st.session_state.folded.append(i); 
                    st.rerun()

    if st.session_state.dealer is not None:
        if st.button("핸드 입력 ➡️"): st.session_state.step = 3; st.rerun()

# --- STEP 3 & 4 통합 카드 선택 컴포넌트 ---
def card_grid_selector(label, target_list, max_count):
    st.subheader(label)
    used_cards = st.session_state.hero_hand + st.session_state.board
    
    # 탭으로 문양 분류
    tab_s = st.tabs(["♠", "♥", "◆", "♣"])
    for i, s_v in enumerate(suits.values()):
        with tab_s[i]:
            cols = st.columns(7)
            for j, r in enumerate(ranks):
                card = f"{r}{s_v}"
                is_used = card in used_cards
                is_selected = card in target_list
                
                btn_label = f"{r}{list(suits.keys())[i]}"
                if cols[j % 7].button(btn_label, key=f"sel_{label}_{card}", 
                                      disabled=is_used and not is_selected,
                                      type="primary" if is_selected else "secondary"):
                    if is_selected:
                        target_list.remove(card)
                    elif len(target_list) < max_count:
                        target_list.append(card)
                    st.rerun()
    st.write(f"선택됨: {', '.join(target_list)}")

# --- STEP 3: 내 핸드 입력 (버튼식) ---
elif st.session_state.step == 3:
    st.title("🎴 Step 3. 내 핸드 선택")
    card_grid_selector("My Hand (2장)", st.session_state.hero_hand, 2)
    
    if len(st.session_state.hero_hand) == 2:
        if st.button("분석 시작 ➡️"): st.session_state.step = 4; st.rerun()

# --- STEP 4: 분석 세션 (보드 버튼식 및 중복 차단) ---
elif st.session_state.step == 4:
    st.title(f"📊 {st.session_state.stage}")
    
    if st.session_state.stage != "Pre-flop":
        max_b = 3 if st.session_state.stage == "Flop" else (4 if st.session_state.stage == "Turn" else 5)
        card_grid_selector(f"Board Cards ({max_b}장)", st.session_state.board, max_b)

    st.divider()
    if st.button("🔍 실시간 데이터 분석"):
        eq, outs = calculate_poker_stats(st.session_state.hero_hand, st.session_state.board)
        st.metric("승률 (Equity)", f"{eq:.1f}%")
        if len(st.session_state.board) < 5: st.metric("아우츠 (Outs)", f"{outs}개")
        
        if eq >= 70: st.success("🔥 유리합니다. 벨류를 키우세요!")
        elif eq >= 45: st.warning("⚖️ 마진 상황입니다. 조심하세요.")
        else: st.error("❌ 불리합니다. 폴드를 고려하세요.")

    st.divider()
    stages = ["Pre-flop", "Flop", "Turn", "River", "Session End"]
    curr_idx = stages.index(st.session_state.stage)
    
    c_nav1, c_nav2 = st.columns(2)
    if st.session_state.stage != "Session End":
        if c_nav2.button("다음 단계 ➡️"):
            st.session_state.stage = stages[curr_idx+1]
            st.rerun()
    else:
        if st.button("🔄 전체 초기화 (Reset)"):
            for key in st.session_state.keys(): del st.session_state[key]
            st.rerun()
    if c_nav1.button("⬅️ 이전 단계"):
        st.session_state.step = 2; st.rerun()
