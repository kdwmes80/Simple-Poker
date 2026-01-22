import streamlit as st
import eval7

# --- 1. 핵심 계산 로직 (Equity & Outs) ---
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

# --- 2. UI 스타일 설정 ---
st.set_page_config(page_title="Poker Pro Master", layout="centered")

st.markdown("""
    <style>
    .stButton>button { width: 100%; border-radius: 8px; font-weight: bold; }
    .folded-unit { opacity: 0.25; filter: grayscale(100%); pointer-events: none; }
    .status-bar { 
        background-color: #1e2129; padding: 12px; border-radius: 10px; 
        border: 1px solid #3498db; margin-bottom: 20px; position: sticky; top: 0; z-index: 999;
    }
    .card-tag { background: #34495e; padding: 2px 8px; border-radius: 4px; margin-right: 4px; color: #fff; font-family: monospace; }
    .mode-tag { font-size: 10px; background: #e74c3c; color: white; padding: 2px 6px; border-radius: 10px; margin-left: 5px; }
    </style>
    """, unsafe_allow_html=True)

# 세션 상태 초기화
if 'step' not in st.session_state: st.session_state.step = 1
if 'folded' not in st.session_state: st.session_state.folded = []
if 'dealer' not in st.session_state: st.session_state.dealer = None
if 'hero_hand' not in st.session_state: st.session_state.hero_hand = []
if 'board' not in st.session_state: st.session_state.board = []
if 'stage' not in st.session_state: st.session_state.stage = "Pre-flop"
if 'last_action' not in st.session_state: st.session_state.last_action = "None"
if 'icm_mode' not in st.session_state: st.session_state.icm_mode = False
if 'pushfold_mode' not in st.session_state: st.session_state.pushfold_mode = False

# 상단 상태바
if st.session_state.step >= 3:
    h_s, b_s = sort_cards(st.session_state.hero_hand), sort_cards(st.session_state.board)
    icm_label = "<span class='mode-tag'>ICM ON</span>" if st.session_state.icm_mode else ""
    pf_label = "<span class='mode-tag'>P/F ON</span>" if st.session_state.pushfold_mode else ""
    st.markdown(f"""
        <div class="status-bar">
            <b>내 핸드:</b> {" ".join([f"<span class='card-tag'>{c}</span>" for c in h_s]) if h_s else "---"}<br>
            <b>보드:</b> {" ".join([f"<span class='card-tag'>{c}</span>" for c in b_s]) if b_s else "---"} {icm_label}{pf_label}
        </div>
    """, unsafe_allow_html=True)

# --- 3. 카드 선택 함수 ---
def card_picker(label, target_list, max_count):
    st.subheader(label)
    suits = {'♠':'s', '♥':'h', '◆':'d', '♣':'c'}
    ranks = ['A','K','Q','J','T','9','8','7','6','5','4','3','2']
    sel_key = f"suit_{label}"
    cols = st.columns(4)
    for i, (s_name, s_val) in enumerate(suits.items()):
        if cols[i].button(s_name, key=f"btn_{label}_{s_val}", type="primary" if st.session_state.get(sel_key) == s_val else "secondary"):
            st.session_state[sel_key] = s_val; st.rerun()
    chosen_suit = st.session_state.get(sel_key)
    if chosen_suit:
        grid = st.columns(7)
        all_used = st.session_state.hero_hand + st.session_state.board
        for idx, r in enumerate(ranks):
            card_code = f"{r}{chosen_suit}"
            is_selected = card_code in target_list
            if grid[idx % 7].button(r, key=f"r_{label}_{card_code}", disabled=card_code in all_used and not is_selected, type="primary" if is_selected else "secondary"):
                if is_selected: target_list.remove(card_code)
                elif len(target_list) < max_count: target_list.append(card_code)
                st.rerun()

# --- 4. 메인 단계 로직 ---
if st.session_state.step == 1:
    st.title("🏟️ 1. 환경 설정")
    st.session_state.total = st.select_slider("테이블 인원", options=range(2, 11), value=9)
    
    # [복구] ICM 및 Push/Fold 토글
    c1, c2 = st.columns(2)
    with c1: st.session_state.icm_mode = st.toggle("🏆 ICM 분석 모드")
    with c2: st.session_state.pushfold_mode = st.toggle("⚔️ Push/Fold 모드")
    
    if st.button("테이블 생성 ➡️"): st.session_state.step = 2; st.rerun()

elif st.session_state.step == 2:
    st.title("🪑 2. 테이블 배치")
    for i in range(0, st.session_state.total, 3):
        cols = st.columns(3)
        for j in range(3):
            idx = i + j
            if idx < st.session_state.total:
                with cols[j]:
                    is_f, is_d = idx in st.session_state.folded, st.session_state.dealer == idx
                    st.markdown(f"<div class='{'folded-unit' if is_f else ''}'>", unsafe_allow_html=True)
                    st.write(f"**{'P0 (Hero)' if idx == 0 else f'P{idx}'}**")
                    if st.button("D", key=f"d{idx}", disabled=is_f or (st.session_state.dealer is not None and st.session_state.dealer != idx), type="primary" if is_d else "secondary"):
                        st.session_state.dealer = idx; st.rerun()
                    st.markdown("</div>", unsafe_allow_html=True)
                    if idx != 0:
                        if st.button("F", key=f"f{idx}"):
                            if is_f: st.session_state.folded.remove(idx)
                            else: 
                                st.session_state.folded.append(idx)
                                if is_d: st.session_state.dealer = None
                            st.rerun()
    if st.session_state.dealer is not None and st.button("다음: 핸드 입력 ➡️"): st.session_state.step = 3; st.rerun()

elif st.session_state.step == 3:
    st.title("🎴 3. 내 핸드 선택")
    card_picker("Hero Hand", st.session_state.hero_hand, 2)
    if len(st.session_state.hero_hand) == 2 and st.button("분석 시작 ➡️"): st.session_state.step = 4; st.rerun()

elif st.session_state.step == 4:
    st.title(f"📊 {st.session_state.stage}")
    if st.session_state.stage != "Pre-flop":
        max_b = {'Flop':3, 'Turn':4, 'River':5}.get(st.session_state.stage, 5)
        card_picker("Board Cards", st.session_state.board, max_b)

    st.divider()
    st.subheader("Villain Action")
    act_cols = st.columns(5)
    for i, act in enumerate(["Check", "Call", "Bet", "Raise", "All-in"]):
        if act_cols[i].button(act): st.session_state.last_action = act; st.rerun()
    
    if st.session_state.last_action in ["Bet", "Raise"]:
        st.number_input("Bet Size (BB)", min_value=0.0, step=0.5)

    if st.button("🔍 분석 실행"):
        eq, outs = calculate_poker_stats(st.session_state.hero_hand, st.session_state.board)
        st.metric("승률 (Equity)", f"{eq:.1f}%")
        st.metric("아우츠 (Outs)", f"{outs}개")
        
        # [모드별 가이드 적용]
        if st.session_state.pushfold_mode and eq < 55:
            st.error("❌ P/F 모드: 폴드 권장 범위입니다.")
        elif st.session_state.icm_mode and eq < 65:
            st.warning("⚠️ ICM 모드: 순위 리스크가 큽니다. 신중하세요.")
        elif eq >= 70: st.success("🔥 유리함")
        elif eq >= 45: st.warning("⚖️ 마진")
        else: st.error("❌ 불리함")

    st.divider()
    stages = ["Pre-flop", "Flop", "Turn", "River", "End"]
    curr_idx = stages.index(st.session_state.stage)
    col_n1, col_n2 = st.columns(2)
    if st.session_state.stage != "End":
        if col_n2.button("다음 단계 ➡️"): st.session_state.stage = stages[curr_idx+1]; st.rerun()
    else:
        if st.button("🔄 리셋"):
            for k in list(st.session_state.keys()): del st.session_state[k]
            st.rerun()
    if col_n1.button("⬅️ 테이블 수정"): st.session_state.step = 2; st.rerun()
