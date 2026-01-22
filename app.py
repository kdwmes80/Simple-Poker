import streamlit as st
import eval7

# --- 1. 정밀 승률 계산 및 가이드 데이터 ---
def calculate_precise_stats(hero_hand, board, iters=3000):
    try:
        if len(hero_hand) < 2: return 0, 0
        hero_c = [eval7.Card(c) for c in hero_hand]
        board_c = [eval7.Card(c) for c in board]
        win_count = 0
        
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

def get_open_range_guide(position):
    ranges = {
        "UTG": "TOP 10-12% (77+, AJs+, KQs, AJo+)",
        "HJ": "TOP 15-18% (55+, A8s+, KTs+, QJs, ATs+)",
        "CO": "TOP 25-30% (22+, A2s+, K8s+, Q9s+, J9s+, T9s)",
        "BTN": "TOP 40-50% (Any Ace, Any Pair, K2s+, Q5s+, J7s+)",
        "SB": "TOP 40-45% (신중한 플레이 필요)",
        "BB": "방어 위주 (상대 오픈 사이즈에 따라 결정)"
    }
    return ranges.get(position, "표준 레인지 가이드 없음")

def sort_cards(card_list):
    rank_order = {'A':14, 'K':13, 'Q':12, 'J':11, 'T':10, '9':9, '8':8, '7':7, '6':6, '5':5, '4':4, '3':3, '2':2}
    return sorted(card_list, key=lambda x: rank_order.get(x[0], 0), reverse=True)

# --- 2. UI 및 세션 관리 ---
st.set_page_config(page_title="Poker Strategy Master Pro", layout="centered")

init_keys = {
    'step': 1, 'hero_hand': [], 'board': [], 'folded': [], 
    'villain_actions': {}, 'stage': "Pre-flop", 
    'icm_mode': False, 'pushfold_mode': False, 'hero_pos': "BTN",
    'total': 9 # total_p 에러 방지를 위해 초기값 설정
}
for k, v in init_keys.items():
    if k not in st.session_state: st.session_state[k] = v

# --- 3. 카드 선택 컴포넌트 ---
def card_picker_pro(label, target_list, max_count):
    st.write(f"**{label}**")
    suits = {'♠':'s', '♥':'h', '◆':'d', '♣':'c'}
    ranks = ['A','K','Q','J','T','9','8','7','6','5','4','3','2']
    sel_key = f"pro_suit_{label}"
    
    cols = st.columns(4)
    for i, (s_name, s_val) in enumerate(suits.items()):
        if cols[i].button(s_name, key=f"s_{label}_{s_val}", type="primary" if st.session_state.get(sel_key) == s_val else "secondary"):
            st.session_state[sel_key] = s_val; st.rerun()
            
    chosen_suit = st.session_state.get(sel_key)
    if chosen_suit:
        all_used = st.session_state.hero_hand + st.session_state.board
        for row in [ranks[:7], ranks[7:]]:
            r_cols = st.columns(7)
            for i, r in enumerate(row):
                card = f"{r}{chosen_suit}"
                is_sel = card in target_list
                if r_cols[i].button(r, key=f"r_{label}_{card}", disabled=card in all_used and not is_sel, type="primary" if is_sel else "secondary"):
                    if is_sel: target_list.remove(card)
                    elif len(target_list) < max_count: target_list.append(card)
                    st.rerun()

# --- 4. 메인 단계별 로직 ---

if st.session_state.step >= 3:
    h_s, b_s = sort_cards(st.session_state.hero_hand), sort_cards(st.session_state.board)
    st.info(f"📍 포지션: **{st.session_state.hero_pos}** | 핸드: **{' '.join(h_s)}** | 보드: **{' '.join(b_s)}**")

if st.session_state.step == 1:
    st.title("🏟️ 1. 포지션 및 환경 설정")
    # total_p 대신 직접 session_state.total에 할당
    st.session_state.total = st.select_slider("테이블 인원", options=range(2, 10), value=9)
    
    if st.session_state.total <= 6: positions = ["UTG", "HJ", "CO", "BTN", "SB", "BB"]
    else: positions = ["UTG", "UTG+1", "UTG+2", "LJ", "HJ", "CO", "BTN", "SB", "BB"]
    
    st.session_state.hero_pos = st.selectbox("나의 포지션", positions[:st.session_state.total])
    
    c1, c2 = st.columns(2)
    st.session_state.icm_mode = c1.toggle("🏆 ICM 분석 모드")
    st.session_state.pushfold_mode = c2.toggle("⚔️ Push/Fold 모드")
    
    st.caption(f"💡 현재 포지션 가이드: {get_open_range_guide(st.session_state.hero_pos)}")
    
    if st.button("설정 완료 ➡️"): st.session_state.step = 2; st.rerun()

elif st.session_state.step == 2:
    st.title(f"🪑 2. {st.session_state.stage} 상대 액션")
    # total_p 에러 수정: st.session_state.total 사용
    if st.session_state.total <= 6: positions = ["UTG", "HJ", "CO", "BTN", "SB", "BB"]
    else: positions = ["UTG", "UTG+1", "UTG+2", "LJ", "HJ", "CO", "BTN", "SB", "BB"]
    
    for p in positions[:st.session_state.total]:
        if p == st.session_state.hero_pos:
            st.warning(f"😎 {p} (Hero)")
            continue
        
        col1, col2, col3 = st.columns([1, 1, 2])
        is_f = p in st.session_state.folded
        col1.write(f"**{p}**")
        if col2.button("Fold", key=f"f_{p}", type="primary" if is_f else "secondary"):
            if is_f: st.session_state.folded.remove(p)
            else: st.session_state.folded.append(p)
            st.rerun()
        
        if not is_f:
            st.session_state.villain_actions[p] = col3.selectbox("Action", ["None", "Check", "Call", "Bet/Raise", "All-in"], key=f"act_{p}")
            
    if st.button("카드 입력 이동 ➡️"): st.session_state.step = 3; st.rerun()

elif st.session_state.step == 3:
    st.title("🎴 3. 카드 입력")
    card_picker_pro("My Hand (2장)", st.session_state.hero_hand, 2)
    if st.session_state.stage != "Pre-flop":
        m_c = {'Flop':3, 'Turn':4, 'River':5}.get(st.session_state.stage, 5)
        card_picker_pro("Board Cards", st.session_state.board, m_c)
    
    if len(st.session_state.hero_hand) == 2:
        if st.button("정밀 분석 실행 ➡️", type="primary"): st.session_state.step = 4; st.rerun()

elif st.session_state.step == 4:
    st.title("🔍 분석 및 밸류 가이드")
    with st.spinner('정밀 시뮬레이션 중...'):
        equity, outs = calculate_precise_stats(st.session_state.hero_hand, st.session_state.board)
    
    c1, c2 = st.columns(2)
    c1.metric("승률 (Equity)", f"{equity:.1f}%")
    if st.session_state.stage != "River":
        c2.metric("아우츠 (Outs)", f"{outs}개")

    is_agg = any(a in ["Bet/Raise", "All-in"] for a in st.session_state.villain_actions.values())
    
    st.subheader("💡 전략 추천")
    if equity >= 75:
        st.success("🔥 **밸류(Value)가 매우 높습니다.** 적극적인 베팅으로 팟 사이즈를 키우세요.")
    elif equity >= 50:
        if is_agg: st.warning("⚖️ 밸류는 있으나 상대의 액션이 강합니다. 콜(Call)로 조절하거나 팟 컨트롤이 필요합니다.")
        else: st.info("✅ 주도권이 있습니다. 컨티뉴에이션 벳(C-Bet)을 고려하세요.")
    elif equity >= 20:
        if st.session_state.pushfold_mode: st.error("⚔️ P/F 모드: 폴드(Fold)를 권장합니다.")
        else: st.warning("⚠️ 드로우 핸드입니다. 팟 오즈가 승률보다 높을 때만 콜하세요.")
    else:
        st.error("❌ 승률이 매우 낮습니다. 체크-폴드(Check-Fold)를 권장합니다.")
        
    with st.expander("📖 포지션 레인지 가이드"):
        st.write(f"**{st.session_state.hero_pos} 포지션 가이드:**")
        st.write(get_open_range_guide(st.session_state.hero_pos))

    st.divider()
    col_l, col_r = st.columns(2)
    if col_r.button("다음 라운드로 ➡️"):
        stages = ["Pre-flop", "Flop", "Turn", "River", "End"]
        curr = stages.index(st.session_state.stage)
        if curr < len(stages)-1:
            st.session_state.stage = stages[curr+1]
            st.session_state.villain_actions = {}
            st.session_state.step = 2
            st.rerun()
    if col_l.button("🔄 게임 리셋"):
        for k in list(st.session_state.keys()): del st.session_state[k]
        st.rerun()
