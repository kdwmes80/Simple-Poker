import streamlit as st
import eval7

# --- 1. 유틸리티 함수 및 로직 ---
def calculate_poker_stats(hero_hand, board):
    try:
        hero_c = [eval7.Card(c) for c in hero_hand]
        board_c = [eval7.Card(c) for c in board]
        win_count, iters = 0, 1000 
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
        return (win_count / iters) * 100
    except: return 0

# 카드 정렬 함수 (A, K, Q... 2 순서)
def sort_cards(card_list):
    if not card_list: return []
    rank_order = {'A':14, 'K':13, 'Q':12, 'J':11, 'T':10, '9':9, '8':8, '7':7, '6':6, '5':5, '4':4, '3':3, '2':2}
    # 카드 형식(예: 'As', 'Td')에서 첫 글자로 정렬
    return sorted(card_list, key=lambda x: rank_order.get(x[0], 0), reverse=True)

# --- 2. UI 스타일 및 세션 설정 ---
st.set_page_config(page_title="Poker Pro Master", layout="centered")

st.markdown("""
    <style>
    .stButton>button { width: 100%; border-radius: 8px; height: 3em; font-weight: bold; font-size: 14px; }
    .folded-unit { opacity: 0.2; filter: grayscale(100%); pointer-events: none; }
    .status-bar { 
        background-color: #1e2129; padding: 12px; border-radius: 10px; 
        border-left: 5px solid #3498db; margin-bottom: 20px; position: sticky; top: 0; z-index: 999;
    }
    .card-tag { background: #34495e; padding: 2px 6px; border-radius: 4px; margin-right: 4px; color: #fff; font-family: monospace; }
    .suit-title { font-size: 18px; font-weight: bold; margin-top: 10px; color: #ecf0f1; }
    </style>
    """, unsafe_allow_html=True)

if 'step' not in st.session_state: st.session_state.step = 1
if 'folded' not in st.session_state: st.session_state.folded = []
if 'dealer' not in st.session_state: st.session_state.dealer = None
if 'hero_hand' not in st.session_state: st.session_state.hero_hand = []
if 'board' not in st.session_state: st.session_state.board = []
if 'stage' not in st.session_state: st.session_state.stage = "Pre-flop"

# 상단 상시 표기 바
if st.session_state.step >= 3:
    hero_sorted = sort_cards(st.session_state.hero_hand)
    board_sorted = sort_cards(st.session_state.board)
    st.markdown(f"""
        <div class="status-bar">
            <b>내 핸드:</b> {" ".join([f"<span class='card-tag'>{c}</span>" for c in hero_sorted]) if hero_sorted else "선택 중..."}<br>
            <b>보드:</b> {" ".join([f"<span class='card-tag'>{c}</span>" for c in board_sorted]) if board_sorted else "없음"}
        </div>
    """, unsafe_allow_html=True)

# --- 3. 카드 선택 컴포넌트 (오류 수정 버전) ---
def card_selector_ui(label, target_list_name, max_count):
    st.subheader(label)
    ranks = ['A','K','Q','J','T','9','8','7','6','5','4','3','2']
    suits = {'♠':'s','♥':'h','◆':'d','♣':'c'}
    
    # 중복 체크용 (내 핸드 + 보드 전체)
    all_selected = st.session_state.hero_hand + st.session_state.board
    current_target = st.session_state[target_list_name]

    for s_name, s_val in suits.items():
        st.markdown(f"<div class='suit-title'>{s_name} {s_name.upper()}</div>", unsafe_allow_html=True)
        cols = st.columns(7)
        for idx, r in enumerate(ranks):
            card_code = f"{r}{s_val}"
            is_in_this_list = card_code in current_target
            is_disabled = card_code in all_selected and not is_in_this_list
            
            if cols[idx % 7].button(f"{r}{s_name}", key=f"btn_{label}_{card_code}", 
                                    type="primary" if is_in_this_list else "secondary",
                                    disabled=is_disabled):
                if is_in_this_list:
                    st.session_state[target_list_name].remove(card_code)
                elif len(current_target) < max_count:
                    st.session_state[target_list_name].append(card_code)
                st.rerun()

# --- 4. 메인 로직 ---
if st.session_state.step == 1:
    st.title("🏟️ Step 1. 인원 설정")
    st.session_state.total = st.select_slider("테이블 인원", options=range(2, 11), value=9)
    if st.button("테이블 생성 ➡️"):
        st.session_state.step = 2
        st.rerun()

elif st.session_state.step == 2:
    st.title("🪑 Step 2. 테이블 배치")
    for i in range(0, st.session_state.total, 3):
        cols = st.columns(3)
        for j in range(3):
            idx = i + j
            if idx < st.session_state.total:
                with cols[j]:
                    is_f, is_d = idx in st.session_state.folded, st.session_state.dealer == idx
                    st.markdown(f"<div class='{'folded-unit' if is_f else ''}'>", unsafe_allow_html=True)
                    st.write(f"**P{idx}**")
                    if st.button(f"D", key=f"d{idx}", disabled=is_f or (st.session_state.dealer is not None and st.session_state.dealer != idx), type="primary" if is_d else "secondary"):
                        st.session_state.dealer = idx
                        st.rerun()
                    if idx != 0:
                        if st.button("Fold" if not is_f else "Unfold", key=f"f{idx}"):
                            if is_f: st.session_state.folded.remove(idx)
                            else: 
                                st.session_state.folded.append(idx)
                                if is_d: st.session_state.dealer = None
                            st.rerun()
                    st.markdown("</div>", unsafe_allow_html=True)
    if st.session_state.dealer is not None:
        if st.button("핸드 입력 이동 ➡️"): st.session_state.step = 3; st.rerun()

elif st.session_state.step == 3:
    st.title("🎴 Step 3. 내 핸드 선택")
    card_selector_ui("My Hand (2장 선택)", 'hero_hand', 2)
    if len(st.session_state.hero_hand) == 2:
        if st.button("분석 세션 시작 ➡️"): st.session_state.step = 4; st.rerun()

elif st.session_state.step == 4:
    st.title(f"📊 {st.session_state.stage}")
    if st.session_state.stage != "Pre-flop":
        max_b = {'Flop':3, 'Turn':4, 'River':5}.get(st.session_state.stage, 5)
        card_selector_ui(f"Board ({max_b}장 선택)", 'board', max_b)

    if st.button("🔍 실시간 분석 실행"):
        equity = calculate_poker_stats(st.session_state.hero_hand, st.session_state.board)
        st.metric("승률 (Equity)", f"{equity:.1f}%")
        if equity >= 70: st.success("🔥 유리함")
        elif equity >= 45: st.warning("⚖️ 마진")
        else: st.error("❌ 불리함")

    st.divider()
    stages = ["Pre-flop", "Flop", "Turn", "River", "End"]
    curr_idx = stages.index(st.session_state.stage)
    if st.session_state.stage != "End":
        if st.button("다음 단계 ➡️"): st.session_state.stage = stages[curr_idx+1]; st.rerun()
    else:
        if st.button("🔄 리셋"):
            for k in list(st.session_state.keys()): del st.session_state[k]
            st.rerun()
