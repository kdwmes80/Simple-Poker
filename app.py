import streamlit as st
import eval7

# --- 1. 유틸리티 함수 ---
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

def sort_cards(card_list):
    if not card_list: return []
    rank_order = {'A':14, 'K':13, 'Q':12, 'J':11, 'T':10, '9':9, '8':8, '7':7, '6':6, '5':5, '4':4, '3':3, '2':2}
    return sorted(card_list, key=lambda x: rank_order.get(x[0], 0), reverse=True)

# --- 2. UI 스타일 및 세션 설정 ---
st.set_page_config(page_title="Poker Master", layout="centered")

st.markdown("""
    <style>
    .stButton>button { width: 100%; border-radius: 8px; font-weight: bold; }
    .status-bar { 
        background-color: #1e2129; padding: 12px; border-radius: 10px; 
        border-left: 5px solid #3498db; margin-bottom: 20px; position: sticky; top: 0; z-index: 999;
    }
    .card-tag { background: #34495e; padding: 2px 6px; border-radius: 4px; margin-right: 4px; color: #fff; }
    .suit-btn { font-size: 20px !important; height: 3em !important; }
    </style>
    """, unsafe_allow_html=True)

if 'step' not in st.session_state: st.session_state.step = 1
if 'folded' not in st.session_state: st.session_state.folded = []
if 'dealer' not in st.session_state: st.session_state.dealer = None
if 'hero_hand' not in st.session_state: st.session_state.hero_hand = []
if 'board' not in st.session_state: st.session_state.board = []
if 'stage' not in st.session_state: st.session_state.stage = "Pre-flop"

# --- [공통] 카드 선택기 함수 ---
def card_picker(label, target_list, max_count):
    st.subheader(label)
    suits = {'♠':'s', '♥':'h', '◆':'d', '♣':'c'}
    ranks = ['A','K','Q','J','T','9','8','7','6','5','4','3','2']
    
    # 1. 문양 선택 (가로 4칸)
    selected_suit_key = f"suit_sel_{label}"
    suit_cols = st.columns(4)
    for i, (s_name, s_val) in enumerate(suits.items()):
        if suit_cols[i].button(s_name, key=f"s_{label}_{s_val}", 
                               type="primary" if st.session_state.get(selected_suit_key) == s_val else "secondary"):
            st.session_state[selected_suit_key] = s_val
            st.rerun()

    # 2. 숫자 선택 (문양이 선택된 경우만 노출)
    chosen_suit = st.session_state.get(selected_suit_key)
    if chosen_suit:
        st.write(f"**{chosen_suit.upper()}** 문양의 숫자를 선택하세요:")
        grid = st.columns(7)
        all_used = st.session_state.hero_hand + st.session_state.board
        
        for idx, r in enumerate(ranks):
            card_code = f"{r}{chosen_suit}"
            is_selected = card_code in target_list
            is_disabled = card_code in all_used and not is_selected
            
            if grid[idx % 7].button(r, key=f"r_{label}_{card_code}", 
                                    disabled=is_disabled,
                                    type="primary" if is_selected else "secondary"):
                if is_selected:
                    target_list.remove(card_code)
                elif len(target_list) < max_count:
                    target_list.append(card_code)
                st.rerun()

# --- 3. 메인 화면 구성 ---

# 상단 상태바
if st.session_state.step >= 3:
    h_s = sort_cards(st.session_state.hero_hand)
    b_s = sort_cards(st.session_state.board)
    st.markdown(f'<div class="status-bar"><b>핸드:</b> {" ".join(h_s)} | <b>보드:</b> {" ".join(b_s)}</div>', unsafe_allow_html=True)

if st.session_state.step == 1:
    st.title("🏟️ 1. 인원 설정")
    st.session_state.total = st.select_slider("인원", options=range(2, 11), value=9)
    if st.button("시작"): st.session_state.step = 2; st.rerun()

elif st.session_state.step == 2:
    st.title("🪑 2. 테이블 (P0=나)")
    for i in range(0, st.session_state.total, 3):
        cols = st.columns(3)
        for j in range(3):
            idx = i + j
            if idx < st.session_state.total:
                with cols[j]:
                    is_f, is_d = idx in st.session_state.folded, st.session_state.dealer == idx
                    st.write(f"**P{idx}**")
                    if st.button("D", key=f"d{idx}", disabled=is_f or (st.session_state.dealer is not None and st.session_state.dealer != idx), type="primary" if is_d else "secondary"):
                        st.session_state.dealer = idx; st.rerun()
                    if idx != 0:
                        if st.button("F", key=f"f{idx}"):
                            if is_f: st.session_state.folded.remove(idx)
                            else: st.session_state.folded.append(idx); st.session_state.dealer = None if is_d else st.session_state.dealer
                            st.rerun()
    if st.session_state.dealer is not None:
        if st.button("다음 ➡️"): st.session_state.step = 3; st.rerun()

elif st.session_state.step == 3:
    st.title("🎴 3. 내 핸드 (2장)")
    card_picker("Hero Hand", st.session_state.hero_hand, 2)
    if len(st.session_state.hero_hand) == 2:
        if st.button("분석 시작 ➡️"): st.session_state.step = 4; st.rerun()

elif st.session_state.step == 4:
    st.title(f"📊 {st.session_state.stage}")
    if st.session_state.stage != "Pre-flop":
        max_b = {'Flop':3, 'Turn':4, 'River':5}.get(st.session_state.stage, 5)
        card_picker("Board", st.session_state.board, max_b)

    if st.button("🔍 분석"):
        equity = calculate_poker_stats(st.session_state.hero_hand, st.session_state.board)
        st.metric("승률", f"{equity:.1f}%")
        
    st.divider()
    stages = ["Pre-flop", "Flop", "Turn", "River", "End"]
    curr_idx = stages.index(st.session_state.stage)
    if st.session_state.stage != "End":
        if st.button("다음 단계"): st.session_state.stage = stages[curr_idx+1]; st.rerun()
    else:
        if st.button("🔄 리셋"):
            for k in list(st.session_state.keys()): del st.session_state[k]
            st.rerun()
