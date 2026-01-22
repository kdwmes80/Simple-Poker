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
    except: return 0, 0

def sort_cards(card_list):
    if not card_list: return []
    rank_order = {'A':14, 'K':13, 'Q':12, 'J':11, 'T':10, '9':9, '8':8, '7':7, '6':6, '5':5, '4':4, '3':3, '2':2}
    return sorted(card_list, key=lambda x: rank_order.get(x[0], 0), reverse=True)

# --- 2. UI 스타일 (간결함 강조) ---
st.set_page_config(page_title="Poker Pro Master", layout="centered")

st.markdown("""
    <style>
    .stButton>button { width: 100%; border-radius: 6px; font-weight: bold; height: 3em; font-size: 14px; }
    .folded-box { opacity: 0.3 !important; filter: grayscale(100%) !important; pointer-events: none; border: 1px solid #444; padding: 5px; border-radius: 8px; }
    .active-box { border: 1px solid #3498db; padding: 5px; border-radius: 8px; margin-bottom: 5px; }
    .status-bar { 
        background-color: #1e2129; padding: 12px; border-radius: 10px; 
        border-bottom: 3px solid #3498db; margin-bottom: 15px; position: sticky; top: 0; z-index: 999;
    }
    .card-tag { background: #34495e; padding: 3px 8px; border-radius: 4px; margin-right: 4px; color: #fff; font-family: monospace; }
    .suit-container { background: #262730; padding: 10px; border-radius: 10px; margin-bottom: 10px; }
    </style>
    """, unsafe_allow_html=True)

# 세션 상태 초기화
states = ['step', 'folded', 'dealer', 'hero_hand', 'board', 'stage', 'last_action', 'icm_mode', 'pushfold_mode']
defaults = [1, [], None, [], [], "Pre-flop", "None", False, False]
for s, d in zip(states, defaults):
    if s not in st.session_state: st.session_state[s] = d

# --- 3. 상단 상태바 ---
if st.session_state.step >= 3:
    h_s, b_s = sort_cards(st.session_state.hero_hand), sort_cards(st.session_state.board)
    st.markdown(f"""
        <div class="status-bar">
            <span style="font-size: 0.8em; color: #3498db;">HAND:</span> {" ".join([f"<span class='card-tag'>{c}</span>" for c in h_s]) if h_s else "---"} 
            <span style="margin-left:10px; font-size: 0.8em; color: #3498db;">BOARD:</span> {" ".join([f"<span class='card-tag'>{c}</span>" for c in b_s]) if b_s else "---"}
        </div>
    """, unsafe_allow_html=True)

# --- 4. 카드 선택 함수 (문양 선택 시에만 숫자 노출) ---
def card_picker(label, target_list, max_count):
    suits = {'♠':'s', '♥':'h', '◆':'d', '♣':'c'}
    ranks = ['A','K','Q','J','T','9','8','7','6','5','4','3','2']
    sel_key = f"active_suit_{label}"
    
    st.write(f"**{label}** ({len(target_list)}/{max_count})")
    
    # 문양 선택 가로 버튼
    scols = st.columns(4)
    for i, (s_name, s_val) in enumerate(suits.items()):
        if scols[i].button(s_name, key=f"s_{label}_{s_val}", 
                           type="primary" if st.session_state.get(sel_key) == s_val else "secondary"):
            st.session_state[sel_key] = s_val
            st.rerun()

    # 문양이 선택된 경우에만 숫자판 등장 (레이아웃 간소화)
    chosen_suit = st.session_state.get(sel_key)
    if chosen_suit:
        st.markdown("<div class='suit-container'>", unsafe_allow_html=True)
        all_used = st.session_state.hero_hand + st.session_state.board
        for row_ranks in [ranks[:7], ranks[7:]]:
            cols = st.columns(7)
            for i, r in enumerate(row_ranks):
                card_code = f"{r}{chosen_suit}"
                is_sel = card_code in target_list
                if cols[i].button(r, key=f"r_{label}_{card_code}", 
                                  disabled=card_code in all_used and not is_sel,
                                  type="primary" if is_sel else "secondary"):
                    if is_sel: target_list.remove(card_code)
                    elif len(target_list) < max_count: target_list.append(card_code)
                    st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)

# --- 5. 메인 흐름 ---
if st.session_state.step == 1:
    st.title("🏟️ 환경 설정")
    st.session_state.total = st.select_slider("인원", options=range(2, 11), value=9)
    c1, c2 = st.columns(2)
    st.session_state.icm_mode = c1.toggle("🏆 ICM")
    st.session_state.pushfold_mode = c2.toggle("⚔️ P/F")
    if st.button("시작 ➡️"): st.session_state.step = 2; st.rerun()

elif st.session_state.step == 2:
    st.title("🪑 테이블")
    for i in range(0, st.session_state.total, 3):
        cols = st.columns(3)
        for j in range(3):
            idx = i + j
            if idx < st.session_state.total:
                with cols[j]:
                    is_f, is_d = idx in st.session_state.folded, st.session_state.dealer == idx
                    st.markdown(f"<div class='{'folded-box' if is_f else 'active-box'}'>", unsafe_allow_html=True)
                    st.write(f"**{'Hero' if idx == 0 else f'P{idx}'}**")
                    if st.button("D", key=f"d{idx}", disabled=is_f, type="primary" if is_d else "secondary"):
                        st.session_state.dealer = idx; st.rerun()
                    st.markdown("</div>", unsafe_allow_html=True)
                    if idx != 0:
                        if st.button("F", key=f"f{idx}"):
                            if is_f: st.session_state.folded.remove(idx)
                            else: 
                                st.session_state.folded.append(idx)
                                if is_d: st.session_state.dealer = None
                            st.rerun()
    if st.session_state.dealer is not None:
        if st.button("카드 입력 ➡️"): st.session_state.step = 3; st.rerun()

elif st.session_state.step == 3:
    st.title("🎴 핸드 선택")
    card_picker("My Hand", st.session_state.hero_hand, 2)
    if len(st.session_state.hero_hand) == 2:
        if st.button("분석 시작 ➡️"): st.session_state.step = 4; st.rerun()

elif st.session_state.step == 4:
    st.title(f"📊 {st.session_state.stage}")
    if st.session_state.stage != "Pre-flop":
        m_count = {'Flop':3, 'Turn':4, 'River':5}.get(st.session_state.stage, 5)
        card_picker("Board", st.session_state.board, m_count)

    st.divider()
    # [수정] Bet/Raise 버튼 통합
    act_list = ["Check", "Call", "Bet/Raise", "All-in"]
    acols = st.columns(4)
    for i, act in enumerate(act_list):
        if acols[i].button(act, type="primary" if st.session_state.last_action == act else "secondary"):
            st.session_state.last_action = act; st.rerun()

    if st.session_state.last_action == "Bet/Raise":
        st.number_input("Amount (BB)", min_value=0.0, step=1.0)

    if st.button("🔍 분석", use_container_width=True):
        eq, outs = calculate_poker_stats(st.session_state.hero_hand, st.session_state.board)
        st.metric("승률", f"{eq:.1f}%", help="상대 핸드 범위 대비 나의 승리 확률")
        if len(st.session_state.board) < 5: st.metric("아우츠", f"{outs}개")
        
    st.divider()
    stages = ["Pre-flop", "Flop", "Turn", "River", "End"]
    curr_idx = stages.index(st.session_state.stage)
    c_prev, c_next = st.columns(2)
    if st.session_state.stage != "End":
        if c_next.button("다음 ➡️"): st.session_state.stage = stages[curr_idx+1]; st.rerun()
    else:
        if st.button("🔄 리셋"):
            for k in list(st.session_state.keys()): del st.session_state[k]
            st.rerun()
    if c_prev.button("⬅️ 테이블"): st.session_state.step = 2; st.rerun()
